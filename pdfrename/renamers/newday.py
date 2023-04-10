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

_URLS_TO_ISSUERS = {
    "\nnewday.co.uk/myamazon\n": "Amazon Platinum MasterCard",
    "\nnewday.co.uk/mypulse\n": "Pulse",
}


@pdfrenamer
def newday_credit_card_statement(
    document: pdf_document.Document,
) -> NameComponents | None:
    logger = _LOGGER.getChild("newday_credit_card_statement")

    # Try first the first page, but if you see an account number on a short page, take the second.
    text_boxes = document[1]
    if len(text_boxes) == 2:
        # 17 characters: 16-digit PAN of the card (Account Number) plus newline.
        # 736501 is the BIN for NewDay/Amazon Platinum.
        if len(text_boxes[0]) == 17 and text_boxes[0].startswith("736501"):
            logger.debug(
                f"{document.original_filename}: possible NewDay statement, looking at the second page."
            )
            text_boxes = document[2]

    if not text_boxes:
        return None

    if "Your Monthly Statement\n" not in text_boxes:
        return None

    for url, issuer in _URLS_TO_ISSUERS.items():
        if url in text_boxes[0]:
            break
    else:
        logger.debug("Unable to find a valid issue for newday statement.")
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

    additional_components = []
    if card_number_match:
        additional_components.append(f"xx-{card_number_match.group(1)}")

    return NameComponents(
        statement_date,
        issuer,
        account_holder_name,
        "Credit Card Statement",
        additional_components=additional_components,
    )
