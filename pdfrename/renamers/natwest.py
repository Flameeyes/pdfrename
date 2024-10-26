# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import enum
import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import drop_honorific


class Bank(enum.StrEnum):
    NATWEST = "NatWest"
    ULSTER_BANK_NI = "Ulster Bank (NI)"


_LOGGER = logging.getLogger(__name__)

_WEBSITES_TO_BANK = {
    "www.ulsterbank.co.uk": Bank.ULSTER_BANK_NI,
    "www.natwest.com": Bank.NATWEST,
}

_PDF_AUTHORS_TO_BANK: dict[bytes | None, str] = {
    b"National Westminster Bank plc": Bank.NATWEST
}


def _bank_name_from_metadata(document: pdf_document.Document) -> Bank | None:
    return _PDF_AUTHORS_TO_BANK.get(document.author)


def _bank_name_from_boxes(document: pdf_document.Document) -> Bank | None:
    first_page = document[1]

    for website, bank_name in _WEBSITES_TO_BANK.items():
        if any(website in box for box in first_page):
            break
    else:
        return None

    return bank_name


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("statement")

    first_page = document[1]

    if (
        not first_page
        or "Statement\n" not in first_page
        or "Period\n" not in first_page
    ):
        return None

    bank_name = _bank_name_from_boxes(document)
    if not bank_name:
        return None

    logger.debug(f"Possible {bank_name} statement.")
    period_line_index = first_page.index("Period\n") + 1
    period_line = first_page[period_line_index]

    logger.debug(f"Found period line: {period_line!r}")

    date_match = re.match(
        r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\n)",
        period_line,
    )
    if date_match is None:
        return None

    statement_date = dateparser.parse(date_match.group(1), languages=["en"])
    if statement_date is None:
        return None

    # The account holder(s) as well as the account type follow the IBAN, either in the same
    # or in different boxes.
    iban_box_index = first_page.find_index_with_match(
        lambda box: box.startswith("IBAN:") or "\nIBAN: " in box
    )
    if iban_box_index is None:
        return None
    logger.debug("Found IBAN box: %r", first_page[iban_box_index])

    # If the following box says "Branch Details" then the details are attached to the IBAN
    # box.
    account_holders_string = first_page[iban_box_index + 1]
    logger.debug("Found possible account holders: %r", account_holders_string)
    if account_holders_string == "Branch Details\n":
        # Extract the account holder from the IBAN box, ignoring the first line.
        account_holders = first_page[iban_box_index].split("\n")[1:-2]
    else:
        account_holders = account_holders_string.split("\n")[:-2]

    return NameComponents(statement_date, bank_name, account_holders, "Statement")


@pdfrenamer
def statement_2023(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("statement_2023")

    if document.title != b"Retail_Statements_V2":
        return None

    bank_name = _bank_name_from_boxes(document)
    if not bank_name:
        return None

    logger.debug(f"Possible {bank_name} 2023 statement.")

    first_page = document[1]

    if not (account_name_box := first_page.find_box_starting_with("Account Name\n")):
        return None

    # The box starts with "Account Name" on one line, and ends with the account type (e.g. "REWARD")
    # on the last line alone.
    account_holders = account_name_box.split("\n")[1:-2]

    # Details are now in a complex summary table box, but we can build it relatively easily.
    summary_index = first_page.index("Summary\n")
    iban_index = first_page.index("IBAN\n")

    summary = {
        first_page[summary_index + i]: first_page[iban_index + i]
        for i in range(2, 16 + 1, 2)
    }

    if not (statement_date_str := summary.get("Statement Date\n")):
        logger.debug("Unable to find statement date in summary: %r", summary)
        return None

    statement_date = dateparser.parse(statement_date_str, languages=["en"])
    assert statement_date is not None

    return NameComponents(statement_date, bank_name, account_holders, "Statement")


_STATEMENT_OF_FEES = "Statement of Fees\n"
_HONORIFICS = {"MR", "MRS"}


@pdfrenamer
def statement_of_fees(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("statement_of_fees")

    first_page = document[1]

    if not first_page or _STATEMENT_OF_FEES not in first_page:
        return None

    if (bank_name := _bank_name_from_boxes(document)) is None:
        return None

    logger.debug(f"Possible {bank_name} statement of fees.")

    # Different documents have the first two boxes inverted, so check which one is the document
    # type, the other is the address.
    if first_page[0] == _STATEMENT_OF_FEES:
        address_box = first_page[1]
    elif first_page[1] == _STATEMENT_OF_FEES:
        address_box = first_page[0]
    else:
        return None

    # This does not seem to happen on _all_ addresses, so for now only check if there's more than 4
    # components in the name. It's a bad heuristics but works for now.
    name_line, _ = address_box.split("\n", 1)
    # Some of the older statements use \x03 as separator instead of space.
    name_line = name_line.replace("\x03", " ")
    name_components = name_line.split(" ")
    if len(name_components) > 4 and drop_honorific(name_line) != name_line:
        account_holders: list[str] = []
        # Okay this is a mess, it means that the names were smashed together.
        recomposed_account_holder: list[str] = []
        for index, name_component in enumerate(name_components):
            if name_component in _HONORIFICS:
                continue
            if index == len(name_components) - 1:
                recomposed_account_holder.append(name_component)
                account_holders.append(" ".join(recomposed_account_holder))
                continue
            for honorific in _HONORIFICS:
                if name_component.endswith(honorific):
                    recomposed_account_holder.append(name_component[: -len(honorific)])
                    account_holders.append(" ".join(recomposed_account_holder))
                    recomposed_account_holder = []
                    break
            else:
                recomposed_account_holder.append(name_component)
    else:
        account_holders = [name_line]

    # This is again misaligned between documents: sometimes the order of the boxes is:
    #   ["Period\n", "Date\n", "From ...", DATE]
    # and sometimes it is
    #   ["From ...", DATE, "Period\n", "Date\n"]
    # but there's only one entry of "From" so that's easy.
    period_line_idx = first_page.find_index_starting_with("From ")
    assert period_line_idx is not None
    date_string = first_page[period_line_idx + 1]

    statement_date = dateparser.parse(date_string, languages=["en"])
    assert statement_date is not None

    return NameComponents(
        statement_date, bank_name, account_holders, "Statement of Fees"
    )


@pdfrenamer
def certificate_of_interest(
    document: pdf_document.Document,
) -> NameComponents | None:
    logger = _LOGGER.getChild("certificate_of_interest")

    first_page = document[1]

    if not first_page or not first_page.find_box_starting_with(
        "Certificate of Interest\n"
    ):
        return None

    if (bank_name := _bank_name_from_boxes(document)) is None:
        return None

    logger.debug(f"Possible {bank_name} certificate of interest.")

    # The account holder(s) as well as the account type follow the IBAN, in its own box.
    iban_box_index = first_page.find_index_starting_with("IBAN: ")
    assert iban_box_index is not None

    account_holders_string = first_page[iban_box_index + 1]
    # Ignore both the account type and the last empty line.
    account_holders = account_holders_string.split("\n")[:-2]

    # Date is harder, because there's no explicit date in the document. We need to accept the tax year
    # end as the date of the document.
    period_line = first_page.find_box_starting_with(
        "This is the interest you were paid"
    )
    assert period_line is not None
    date_match = re.search(
        r"during the tax year ending ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n", period_line
    )
    assert date_match

    document_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert document_date is not None

    return NameComponents(
        document_date, bank_name, account_holders, "Certificate of Interest"
    )


@pdfrenamer
def certificate_of_interest_2023(
    document: pdf_document.Document,
) -> NameComponents | None:
    logger = _LOGGER.getChild("certificate_of_interest_2023")

    if (bank_name := _bank_name_from_metadata(document)) is None:
        return None

    if document.subject != b"Certificate of Interest":
        return None

    logger.debug(f"Possible {bank_name} certificate of interest.")

    first_page = document[1]

    tax_year_box = first_page.find_box_starting_with("Tax year ending ")
    assert tax_year_box is not None

    (date_match,) = first_page.find_all_matching_regex(
        re.compile("^Tax year ending ([0-9]{1,2}[a-z]{2} [A-Z][a-z]+ [0-9]{4})\n$")
    )

    document_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert document_date is not None

    (account_name,) = first_page.find_all_matching_regex(
        re.compile(".* you were paid on your (.+) during the tax year.*")
    )

    return NameComponents(
        document_date, bank_name, account_name.group(1), "Certificate of Interest"
    )
