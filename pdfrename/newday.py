# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
from typing import Optional

import dateparser

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .lib import pdf_document
from .utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def amazon_platinum_statement(
    document: pdf_document.Document,
) -> Optional[NameComponents]:
    logger = _LOGGER.getChild("amazon_platinum_statement")

    # Try first the first page, but if you see an account number on a short page, take the second.
    text_boxes = document[1]
    if len(text_boxes) == 2:
        # 17 characters: 16-digit PAN of the card (Account Number) plus newline.
        # 736501 is the BIN for NewDay/Amazon Platinum.
        if len(text_boxes[0]) == 17 and text_boxes[0].startswith("736501"):
            logger.debug(f"{document.original_filename}: possible NewDay statement, looking at the second page.")
            text_boxes = document[2]

    if (
        "newday.co.uk/myamazon\n" not in text_boxes[0]
        or "Your Monthly Statement\n" not in text_boxes
    ):
        return None

    date_box = text_boxes.find_box_starting_with("Statement date: ")
    assert date_box

    statement_date = dateparser.parse(
        date_box[len("Statement date: ") :], languages=["en"]
    )

    date_idx = text_boxes.index(date_box)
    address_box = text_boxes[date_idx - 1]

    account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(
        statement_date,
        "Amazon Platinum MasterCard",
        account_holder_name,
        "Statement",
    )
