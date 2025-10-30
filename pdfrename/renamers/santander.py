# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re
from collections.abc import Sequence

import dateparser
from more_itertools import one

from ..doctypes.en import CREDIT_CARD_STATEMENT, STATEMENT, STATEMENT_OF_FEES
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import (
    extract_account_holder_from_address,
    find_box_starting_with,
    normalize_account_holder_name,
)

_LOGGER = logging.getLogger(__name__)

_SERVICE_NAME = "Santander"

# This matches both 18th Oct 2024 and 3rd December 2023, which are
# both commonly used date formats within Santander documents!
_DATE_REGEX_COMPONENT = "[0-9]{1,2}(?:[a-z]{2})? [A-Z][a-z]{2,} [0-9]{4}"


def _extract_account_holders(address_box: str) -> Sequence[str]:
    extracted_name = extract_account_holder_from_address(address_box)

    # In case of joint accounts!
    if "&" in extracted_name:
        return tuple(name.strip() for name in extracted_name.split("&"))
    else:
        return (extracted_name,)


@pdfrenamer
def current_account_statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("santander.current_account_statement")
    text_boxes = document[1]

    is_santander_select = "Select Current Account\n" in text_boxes
    is_santander_123 = "1l2l3 Current Account earnings\n" in text_boxes

    if not is_santander_123 and not is_santander_select:
        return None

    # Always include the account holder name. This is extracted from the address,
    # which precedes two boxes like these: ('? \n', '%%SSC\n')
    ssc_idx = text_boxes.index("%%SSC\n")
    if ssc_idx is None or ssc_idx < 2:
        return None

    address_box = text_boxes[ssc_idx - 2]

    logger.debug(f"Found address: {address_box!r}")
    account_holders = _extract_account_holders(address_box)

    period_line = text_boxes.find_box_starting_with("Your account summary for  \n")
    assert period_line is not None

    logger.debug(f"found period specification: {period_line!r}")

    period_match = re.match(
        rf"^Your account summary for  \n{_DATE_REGEX_COMPONENT} to ({_DATE_REGEX_COMPONENT})\n$",
        period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert statement_date is not None

    return NameComponents(
        statement_date,
        _SERVICE_NAME,
        account_holders,
        STATEMENT,
    )


@pdfrenamer
def credit_card_statement(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("santander.credit_card_statement")

    if "Santander Credit Card \n" not in text_boxes:
        return None

    # Could be an annual statement, look for it.
    annual_statement_period_line = find_box_starting_with(
        text_boxes, "Annual Statement:"
    )
    if annual_statement_period_line is not None:
        return None

    # Always include the account holder name, which is found in the second text box.
    account_holder_name = extract_account_holder_from_address(text_boxes[1])

    statement_period_line = find_box_starting_with(text_boxes, "Account summary as at:")
    assert statement_period_line is not None

    logger.debug(f"found period specification: {statement_period_line!r}")

    period_match = re.match(
        rf"^Account summary as at: ({_DATE_REGEX_COMPONENT}) for card number ending ([0-9]{{4}})\n$",
        statement_period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    assert statement_date is not None

    return NameComponents(
        statement_date,
        _SERVICE_NAME,
        account_holder_name,
        CREDIT_CARD_STATEMENT,
        account_number=f"xx-{period_match.group(2)}",
    )


@pdfrenamer
def credit_card_annual_statement(
    document: pdf_document.Document,
) -> NameComponents | None:
    logger = _LOGGER.getChild("credit_card_annual_statement")

    first_page = document[1]

    if not any(
        first_page.find_all_matching_regex(re.compile("^Santander Credit Card ?\n$"))
    ):
        return None

    try:
        annual_statement_match = one(
            first_page.find_all_matching_regex(
                re.compile(
                    r"(?:Account Holder Name: (?P<account_holder_name>[\w\s]+)\n)?"
                    rf"Annual Statement: {_DATE_REGEX_COMPONENT} to (?P<statement_end_date>{_DATE_REGEX_COMPONENT})\n"
                    r"Account: .* card number ending (?P<card_number>[0-9]{4})\n$"
                )
            )
        )
    except ValueError:
        return None

    logger.debug(
        "Possible Santander Credit Card Annual Statement: %r",
        annual_statement_match.groupdict(),
    )

    # If the account holder name was not part of the statement information, fall back to the
    # address.
    account_holder_name = annual_statement_match.group("account_holder_name")
    if account_holder_name is None:
        # Always include the account holder name, which is found in the second text box.
        account_holder_name = extract_account_holder_from_address(first_page[1])

    statement_date = dateparser.parse(
        annual_statement_match.group("statement_end_date"), languages=["en"]
    )
    assert statement_date is not None

    card_number = annual_statement_match.group("card_number")

    return NameComponents(
        statement_date,
        _SERVICE_NAME,
        account_holder_name,
        CREDIT_CARD_STATEMENT,
        account_number=f"xx-{card_number}",
    )


@pdfrenamer
def credit_card_statement_2023(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("santander.credit_card")

    if "Santander Credit Card\n" not in text_boxes:
        return None

    if (
        statement_period_line := find_box_starting_with(
            text_boxes, "Account summary as at:"
        )
    ) is None:
        logger.debug("statement period not found, ignoring.")
        return None

    # Always include the account holder name, which is found in the first text box.
    account_holder_name = extract_account_holder_from_address(text_boxes[0])

    logger.debug(f"found period specification: {statement_period_line!r}")

    period_match = re.match(
        rf"^Account summary as at: ({_DATE_REGEX_COMPONENT}) for card number ending ([0-9]{{4}})\n$",
        statement_period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    assert statement_date is not None

    return NameComponents(
        statement_date,
        "Santander",
        account_holder_name,
        CREDIT_CARD_STATEMENT,
        account_number=f"xx-{period_match.group(2)}",
    )


@pdfrenamer
def statement_of_fees(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("santander.statement_of_fees")

    if (
        not find_box_starting_with(text_boxes, "Santander UK plc\n")
        or "Statement of Fees\n" not in text_boxes
    ):
        return None

    # Always include the account holder name, which is found in the fourth text box.
    address_box = text_boxes[3]
    logger.debug(f"Found address: {address_box!r}")
    account_holders = _extract_account_holders(address_box)

    # Find the account this refers to. It's the text box after the title column.
    # account_idx = text_boxes.index("Account\n")
    # account_type = text_boxes[account_idx + 1].strip().title()

    # Find the date this statement was issued. It's the second text box after tht
    # title column (why?)
    date_idx = text_boxes.index("Date\n")
    date_str = text_boxes[date_idx + 2]

    # Unlike the other documents, this uses a normal date format.
    statement_date = datetime.datetime.strptime(date_str, "%d/%m/%Y\n")

    return NameComponents(
        statement_date,
        _SERVICE_NAME,
        account_holders,
        STATEMENT_OF_FEES,
    )


@pdfrenamer
def annual_account_summary(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("santander.annual_account_summary")

    if len(text_boxes) < 31:
        return None

    annual_account_summary_period_line = find_box_starting_with(
        text_boxes, "Your Account Summary for "
    )

    if not annual_account_summary_period_line:
        return None

    account_holder_name = extract_account_holder_from_address(text_boxes[3])

    _, initials, surname = account_holder_name.split(" ", 2)
    initials = " ".join(list(initials)).upper()
    account_holder_name = " ".join([initials, surname])

    # account_type = text_boxes[30].split(":", 1)[0].strip().title()

    logger.debug(f"found period specification: {annual_account_summary_period_line!r}")
    logger.debug(f"possible account: {text_boxes[30]}")

    period_match = re.match(
        rf"^Your Account Summary for {_DATE_REGEX_COMPONENT} to ({_DATE_REGEX_COMPONENT})\n$",
        annual_account_summary_period_line,
    )
    if not period_match:
        return None

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert statement_date is not None

    return NameComponents(
        statement_date,
        _SERVICE_NAME,
        account_holder_name,
        "Annual Account Summary",
    )


@pdfrenamer
def notice_of_electronic_funds_transfer(
    document: pdf_document.Document,
) -> NameComponents | None:
    if not (first_page := document[1]):
        return None

    if "Call us on: 0330 9 123 123\n" not in first_page:
        return None

    account_number_box = one(
        first_page.find_all_matching_regex(
            re.compile(
                r"Sort Code: 0901\d\d\nAccount Number: (\d+)\n", flags=re.IGNORECASE
            )
        )
    )
    account_number_index = first_page.index(account_number_box.group(0))
    account_number = account_number_box.group(1)

    date = dateparser.parse(first_page[account_number_index + 1], languages=["en"])
    assert date is not None

    account_holder_re = re.compile(r"^Dear (.*)\n$")

    recipient_box = first_page.find_box_with_match(
        lambda box: bool(account_holder_re.match(box))
    )
    assert recipient_box is not None

    recipient_match = account_holder_re.match(recipient_box)
    assert recipient_match is not None

    account_holder = normalize_account_holder_name(recipient_match.group(1), True)

    return NameComponents(
        date=date,
        service_name=_SERVICE_NAME,
        account_holder=(account_holder,),
        account_number=account_number,
        document_type="Notice Of An Electronic Funds Transfer",
    )
