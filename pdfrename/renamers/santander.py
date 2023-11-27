# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re
from typing import Sequence

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address, find_box_starting_with


def _extract_account_holders(address_box: str) -> Sequence[str]:
    extracted_name = extract_account_holder_from_address(address_box)

    # In case of joint accounts!
    if "&" in extracted_name:
        return extracted_name.split("&")
    else:
        return (extracted_name,)


@pdfrenamer
def current_account_statement(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("santander.current_account_statement")

    is_santander_select = "Select Current Account\n" in text_boxes
    is_santander_123 = "1l2l3 Current Account earnings\n" in text_boxes

    if not is_santander_123 and not is_santander_select:
        return None

    # Always include the account holder name, which is found in the third text box.
    address_box = text_boxes[2]
    logger.debug(f"Found address: {address_box!r}")
    account_holders = _extract_account_holders(address_box)

    period_line = find_box_starting_with(text_boxes, "Your account summary for  \n")
    assert period_line is not None

    logger.debug(f"found period specification: {period_line!r}")

    period_match = re.match(
        r"^Your account summary for  \n[0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4} to ([0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4})\n$",
        period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert statement_date is not None

    if is_santander_select:
        account_type = "Select Current Account"
    elif is_santander_123:
        account_type = "123 Current Account"

    return NameComponents(
        statement_date,
        "Santander",
        account_holders,
        account_type,
        additional_components=("Statement",),
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
        r"^Account summary as at: ([0-9]{1,2}[a-z]{2} [A-Z][a-z]+ [0-9]{4}) for card number ending ([0-9]{4})\n$",
        statement_period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    assert statement_date is not None

    return NameComponents(
        statement_date,
        "Santander",
        account_holder_name,
        "Credit Card Statement",
        additional_components=(f"xx-{period_match.group(2)}",),
    )


@pdfrenamer
def credit_card_annual_statement(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("santander.credit_card_annual_statement")

    if (
        "Santander Credit Card \n" not in text_boxes
        and "Santander Credit Card\n" not in text_boxes
    ):
        return None

    # Always include the account holder name, which is found in the second text box.
    account_holder_name = extract_account_holder_from_address(text_boxes[1])

    # Could be an annual statement, look for it.
    annual_statement_period_line = find_box_starting_with(
        text_boxes, "Annual Statement:"
    )
    if annual_statement_period_line is None:
        return None

    logger.debug(f"found period specification: {annual_statement_period_line!r}")

    period_match = re.match(
        r"^Annual Statement: [0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4} to ([0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4})\nAccount: .* card number ending ([0-9]{4})\n$",
        annual_statement_period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    assert statement_date is not None

    return NameComponents(
        statement_date,
        "Santander",
        account_holder_name,
        "Credit Card Annual Statement",
        additional_components=(f"xx-{period_match.group(2)}",),
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
        r"^Account summary as at: ([0-9]{1,2}[a-z]{2} [A-Z][a-z]+ [0-9]{4}) for card number ending ([0-9]{4})\n$",
        statement_period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    assert statement_date is not None

    return NameComponents(
        statement_date,
        "Santander",
        account_holder_name,
        "Credit Card Statement",
        additional_components=(f"xx-{period_match.group(2)}",),
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
    account_idx = text_boxes.index("Account\n")
    account_type = text_boxes[account_idx + 1].strip().title()

    # Find the date this statement was issued. It's the second text box after tht
    # title column (why?)
    date_idx = text_boxes.index("Date\n")
    date_str = text_boxes[date_idx + 2]

    # Unlike the other documents, this uses a normal date format.
    statement_date = datetime.datetime.strptime(date_str, "%d/%m/%Y\n")

    return NameComponents(
        statement_date,
        "Santander",
        account_holders,
        account_type,
        additional_components=("Statement of Fees",),
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

    account_type = text_boxes[30].split(":", 1)[0].strip().title()

    logger.debug(f"found period specification: {annual_account_summary_period_line!r}")
    logger.debug(f"possible account: {text_boxes[30]}")

    period_match = re.match(
        r"^Your Account Summary for [0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n$",
        annual_account_summary_period_line,
    )

    assert period_match

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert statement_date is not None

    return NameComponents(
        statement_date,
        "Santander",
        account_holder_name,
        account_type,
        additional_components=("Annual Account Summary",),
    )
