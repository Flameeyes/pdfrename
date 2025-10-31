# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def bill(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bill")

    first_page = document[1]
    if not first_page:
        return None

    enel_address_index = first_page.find_index_starting_with(
        "Enel Energia - Mercato libero dell'energia\n"
    )
    if enel_address_index is None:
        return None

    # Late 2019: the ENEL address is at the beginning, the address is two boxes before the
    # payment due date.
    due_date_idx = first_page.find_index_starting_with("Entro il ")
    if due_date_idx is None:
        return None

    address_box = first_page[due_date_idx - 2]

    # In 2020: the account holder address is _before_ the ENEL address. We can tell if we
    # got the wrong address box if it's too short in lines.
    if address_box.count("\n") < 2:
        address_box_index = enel_address_index - 1
        address_box = first_page[address_box_index]

    account_holder_name = extract_account_holder_from_address(address_box)
    logger.debug(f"Possible account holder found: {account_holder_name!r}")

    # In 2018, the address was before the customer number instead, try again.
    if account_holder_name == "Periodo":
        customer_id_box_index = first_page.find_index_starting_with("N° CLIENTE\n")
        assert customer_id_box_index is not None

        address_box = first_page[customer_id_box_index - 1]
        account_holder_name = extract_account_holder_from_address(address_box)

    # Older bills had an explicit box for the invoice number, followed by the date.
    # New bills have a lot more text so we need to extract that.
    invoice_number_index = first_page.find_index_starting_with("N. Fattura ")
    if invoice_number_index is None:
        logger.debug("Unable to find invoice number, probably newer format.")
        return None

    date_string = first_page[invoice_number_index + 1]
    bill_date = datetime.datetime.strptime(date_string, "Del %d/%m/%Y\n")

    return NameComponents(
        bill_date,
        "Enel Energia",
        account_holder_name,
        "Bolletta",
    )


def _find_and_extract_date_and_document_number(
    page: pdf_document.PageTextBoxes, expression: re.Pattern[str]
) -> tuple[datetime.datetime | None, str | None]:
    if not (
        date_box := page.find_box_with_match(lambda box: bool(expression.search(box)))
    ):
        return None

    date_match = expression.search(date_box)
    assert date_match is not None  # It's safe, or we wouldn't have matched earlier!

    date_string = date_match.group("date")
    return (
        datetime.datetime.strptime(date_string, "%d/%m/%Y"),
        date_match.group("docnumber"),
    )


_DATE_EXTRACTION_2021_RE = re.compile(
    r".*\nN. Fattura (?P<docnumber>.*)\nDel (?P<date>[0-9]{2}/[0-9]{2}/[0-9]{4})\n.*",
    flags=re.MULTILINE | re.DOTALL,
)


@pdfrenamer
def bill_2021(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bill_2021")

    first_page = document[1]
    if not first_page:
        return None

    try:
        more_info_index = first_page.index(
            "Per maggiori informazioni vedi il regolamento sul sito enel.it\n"
        )
    except ValueError:
        return None

    account_holder_name = extract_account_holder_from_address(
        first_page[more_info_index + 1]
    )
    logger.debug(f"Possible account holder found: {account_holder_name!r}")

    # There's a lot of text running together in the same box as the date, we can't easily
    # search for a prefix, so we actually re-use the regex.
    bill_date, document_number = _find_and_extract_date_and_document_number(
        first_page, _DATE_EXTRACTION_2021_RE
    )
    assert bill_date

    return NameComponents(
        bill_date,
        "Enel Energia",
        account_holder_name,
        "Bolletta",
        document_number=document_number,
    )


_DATE_EXTRACTION_2023_RE = re.compile(
    r"[Ff]attura elettronica n. (?P<docnumber>\d+) del (?P<date>[0-9]{2}/[0-9]{2}/[0-9]{4}) ",
    flags=re.MULTILINE | re.DOTALL,
)


@pdfrenamer
def bill_2023(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bill_2023")

    first_page = document[1]
    if not first_page:
        return None

    if first_page.find_box_starting_with(
        "Enel Energia - Mercato libero dell'energia \n"
    ):
        service = "Enel Energia"
    elif (
        first_page.find_box_starting_with("Enel Energia\n") and "FIBRA\n" in first_page
    ):
        service = "Enel Fibra"
    else:
        return None

    logger.debug("Possible %s 2023 bill.", service)

    if (bill_timeframe_idx := first_page.find_index_starting_with("Periodo ")) is None:
        return None

    account_holder_idx = bill_timeframe_idx - 1

    account_holder_name = extract_account_holder_from_address(
        first_page[account_holder_idx]
    )

    logger.debug(f"Possible account holder found: {account_holder_name!r}")

    account_number_box = first_page.find_box_starting_with("N° Cliente")
    account_number_match = re.search(r"N° Cliente\n(\d+)\s", account_number_box)
    account_number = account_number_match.group(1)

    # There's a lot of text running together in the same box as the date, we can't easily
    # search for a prefix, so we actually re-use the regex.
    bill_date, document_number = _find_and_extract_date_and_document_number(
        first_page, _DATE_EXTRACTION_2023_RE
    )
    assert bill_date

    return NameComponents(
        bill_date,
        service,
        account_holder_name,
        "Bolletta",
        account_number=account_number,
        document_number=document_number,
    )
