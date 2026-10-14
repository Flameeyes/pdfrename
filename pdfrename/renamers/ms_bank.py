# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..doctypes.en import CREDIT_CARD_STATEMENT, STATEMENT
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)
_SERVICE = "M&S Bank"
_STATEMENT_IDENTIFIER = "Your M&S Credit Card Statement \n"


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("ms_bank.statement")
    text_boxes = document[1]

    if not text_boxes or "M&S Bank" not in text_boxes[-1]:
        return None

    account_name_box = text_boxes.find_box_starting_with("Account Name\n")
    assert account_name_box

    account_holder_name = account_name_box.split("\n")[1].strip()

    # The statement period is just before the account name box.
    period_box_index = text_boxes.index(account_name_box) - 1
    period_line = text_boxes[period_box_index]

    logger.debug(f"found period specification {period_line!r}")

    period_match = re.search(
        r"^[0-9]{2} [A-Z][a-z]+(?: [0-9]{4})? to ([0-9]{2} [A-Z][a-z]+ [0-9]{4})\\n$",
        period_line,
    )
    assert period_match

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert statement_date

    return NameComponents(
        statement_date,
        _SERVICE,
        account_holder_name,
        STATEMENT,
    )


@pdfrenamer
def credit_card_statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("credit_card_statement")
    first_page = document[1]

    # Cheap, specific identification first.
    if _STATEMENT_IDENTIFIER not in first_page:
        return None

    logger.debug("Found likely M&S Bank credit card statement.")

    # Find statement date and account number boxes by index (they're predictable in this document type)
    # Based on the sample data, we know:
    # Statement date is in box 21: 'Statement Date: \n19 June 2026 \n'

    # Extract statement date from box 21
    statement_date_box = first_page[21]
    # Use flexible regex to handle different whitespace
    statement_date_match = re.search(
        r"Statement Date:\s+([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\s*", statement_date_box
    )
    if not statement_date_match:
        return None

    statement_date_str = statement_date_match.group(1)
    statement_date = dateparser.parse(statement_date_str, languages=["en"])
    assert statement_date

    # Extract account number from box 20
    account_number_box = first_page[20]
    account_number_match = re.search(
        r"Account Number:\s+([0-9 ]+)\s*", account_number_box
    )
    if not account_number_match:
        return None

    # Format account number to show only last 4 digits for privacy
    full_account_number = account_number_match.group(1).replace(" ", "")
    # Show only last 4 digits for privacy
    account_number = f"xx-{full_account_number[-4:]}"

    # Extract account holder from the address box
    account_holder_box = first_page.find_box_starting_with("%MAIL_BARCODE \n")
    if not account_holder_box:
        return None
    account_holder = account_holder_box.strip().split("\n")[1].strip()

    # Debug output
    logger.debug(
        f"Extracted data - Date: {statement_date}, Holder: {account_holder}, Account: {account_number}"
    )

    return NameComponents(
        statement_date,
        _SERVICE,
        account_holder,
        CREDIT_CARD_STATEMENT,
        account_number=account_number,
    )
