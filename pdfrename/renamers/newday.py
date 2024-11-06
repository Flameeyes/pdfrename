# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

_URLS_TO_ISSUERS = (
    (re.compile(r"\bnewday.co.uk/myamazon\n"), "Amazon Platinum MasterCard"),
    (re.compile(r"\bnewday.co.uk/mypulse\n"), "Pulse"),
)

# 17 characters: 16-digit PAN of the card (Account Number) plus newline.
# 736501 is the BIN for NewDay.
_NEWDAY_BIN_PATTERN = re.compile(r"^736501\d{10}\n$")


@pdfrenamer
def newday_credit_card_statement(
    document: pdf_document.Document,
) -> NameComponents | None:
    logger = _LOGGER.getChild("newday_credit_card_statement")

    # Try first the first page, but if you see an account number on a short page, take the second.
    text_boxes = document[1]
    if len(text_boxes) == 2:
        if _NEWDAY_BIN_PATTERN.match(text_boxes[0]):
            logger.debug(
                "%s: possible NewDay statement, looking at the second page.",
                document.original_filename,
            )
            text_boxes = document[2]
    elif not set(text_boxes.find_all_matching_regex(_NEWDAY_BIN_PATTERN)):
        return None

    if not text_boxes:
        return None

    logger.debug("%s: possible NewDay statement.", document.original_filename)

    if (
        "Your Monthly Statement\n" not in text_boxes
        and not text_boxes.find_box_starting_with("Your monthly statement\n")
    ):
        return None

    if "newday.co.uk/" in text_boxes[0]:
        manage_link_box = text_boxes[0]
    elif "newday.co.uk/" in text_boxes[-1]:
        manage_link_box = text_boxes[-1]
    else:
        logger.debug("%s: unable to find management link.", document.original_filename)
        return None

    for url, issuer in _URLS_TO_ISSUERS:
        if url.search(manage_link_box):
            break
    else:
        logger.debug(
            "%s: unable to find a valid issuer for newday statement.",
            document.original_filename,
        )
        return None

    date_box = text_boxes.find_box_starting_with("Statement date: ")
    assert date_box

    statement_date = dateparser.parse(
        date_box[len("Statement date: ") :], languages=["en"]
    )
    assert statement_date is not None

    date_idx = text_boxes.index(date_box)
    address_box = text_boxes[date_idx - 1]

    account_holder_name = extract_account_holder_from_address(address_box)

    account_number_box = text_boxes.find_box_starting_with("Account number ")
    if account_number_box:
        card_number_match = re.match(
            "^Account number [0-9]{12}([0-9]{4})\n$", account_number_box
        )
    else:
        account_number_box_index = text_boxes.index("Account number\n")
        if account_number_box_index:
            card_number_box = text_boxes[account_number_box_index + 1]
            card_number_match = re.match("^[0-9]{12}([0-9]{4})\n$", card_number_box)

    account_number = None
    if card_number_match:
        account_number = f"xx-{card_number_match.group(1)}"

    return NameComponents(
        statement_date,
        issuer,
        account_holder_name,
        "Credit Card Statement",
        account_number=account_number,
    )
