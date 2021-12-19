# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from typing import Optional

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address, find_box_starting_with

_LOGGER = logging.getLogger(__name__)


_DOCUMENT_TYPES = {
    "Your payment plan.\n": "Payment Plan",
    "Your new payment plan.\n": "Payment Plan",
    "Your water and wastewater bill.\n": "Bill",
    "Your new bill and payment plan.\n": "Bill",
    "Your final bill.\n": "Bill",
    "Your new bill.\n": "Bill",
}


@pdfrenamer
def bill(
    document: pdf_document.Document,
) -> Optional[NameComponents]:
    logger = _LOGGER.getChild("bill")

    text_boxes = document[1]
    if not text_boxes:
        return None

    # There are at least two different possible boxes as the bottom of page 1 since 2017,
    # but they all include a link to TW's website.
    is_thameswater = (
        "thameswater.co.uk/" in text_boxes[-1]
        or "thameswater.co.uk/myaccount\n" in text_boxes
    )

    if not is_thameswater:
        return None

    # This is a marker that the bill is from the new (2021) system that is different from
    # what was there before.
    thameswater_2021 = "Moving home?\nthameswater.co.uk/myaccount\n" in text_boxes
    if thameswater_2021:
        logger.debug("thameswater: appears to be a 2021 Thames Water document.")

    assert text_boxes[0].startswith("Page 1 of ")

    date_line = find_box_starting_with(text_boxes, "Date\n")
    logger.debug(f"found date line: {date_line!r}")
    date_match = re.search("^Date\n([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n", date_line)
    assert date_match

    document_date = dateparser.parse(date_match.group(1), languages=["en"])

    try:
        # First try to leverage the more modern (2020/21) template, looking for
        # a box with "Account balance" (possibly followed by "(in credit)") on it.

        document_subject_index = (
            text_boxes.find_index_starting_with("Account balance") - 1
        )
    except ValueError:
        if thameswater_2021:
            logger.debug(
                "thameswater: failed to find the document subject for 2021 document."
            )
            return None

        # If that doesn't work, try the old method of using the 8th box, but that only
        # works for older bills not newer ones.
        document_subject_index = 7

    document_subject = text_boxes[document_subject_index]
    logger.debug(f"document subject: {document_subject!r}")

    document_type = _DOCUMENT_TYPES.get(document_subject, "Other")

    address_box = text_boxes[document_subject_index - 1]
    if address_box.startswith("@"):
        # This is an odd one — older templates had a vertical box with a code.
        # If the address looks like it's starting with an @, check one before.
        address_box = text_boxes[document_subject_index - 2]

    account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(
        document_date,
        "Thames Water",
        account_holder_name,
        document_type,
    )


@pdfrenamer
def letter(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("thameswater.letter")

    if "Thames Water Utilities Limited," not in text_boxes[-1]:
        return None

    date_line = find_box_starting_with(text_boxes, "Date\n")
    if not date_line:
        return None

    logger.debug(f"found date line: {date_line!r}")
    date_match = re.search("^Date\n([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n", date_line)
    assert date_match

    document_date = dateparser.parse(date_match.group(1), languages=["en"])

    account_holder_name = extract_account_holder_from_address(text_boxes[0])

    return NameComponents(document_date, "Thames Water", account_holder_name, "Letter")
