# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


_DOCUMENT_TYPES = {
    "Your payment plan.\n": "Payment Plan",
    "Your new payment plan.\n": "Payment Plan",
    "Your water and wastewater bill.\n": "Bill",
    "Your new bill and payment plan.\n": "Bill",
    "Your final bill.\n": "Bill",
    "Your new bill.\n": "Bill",
}


def _extract_date(date_box: str) -> datetime.datetime:
    date_match = re.search("\n([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n", date_box)
    assert date_match

    document_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert document_date is not None

    return document_date


@pdfrenamer
def bill(
    document: pdf_document.Document,
) -> NameComponents | None:
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

    date_line = text_boxes.find_box_starting_with("Date\n")
    assert date_line is not None
    document_date = _extract_date(date_line)

    # First try to leverage the more modern (2020/21) template, looking for
    # a box with "Account balance" (possibly followed by "(in credit)") on it.
    account_balance_index = text_boxes.find_index_starting_with("Account balance")
    if account_balance_index is not None:
        document_subject_index = account_balance_index - 1
    elif thameswater_2021:
        logger.debug(
            "thameswater: failed to find the document subject for 2021 document."
        )
        return None
    else:
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
def bill_2022(document: pdf_document.Document) -> NameComponents | None:
    text_boxes = document[1]
    if not text_boxes:
        return None

    if not any("thameswater.co.uk/myaccount\n" in box for box in text_boxes):
        return None

    # Old bill (2021 and earlier), or newer bills (2023). Ignore it.
    if text_boxes[0].startswith("Page 1 of "):
        return None

    if (
        "Your latest bill\n" not in text_boxes
        and "Your bill and payment plan\n" not in text_boxes
    ):
        return None

    account_holder_name = extract_account_holder_from_address(text_boxes[0])

    date_line = text_boxes.find_box_starting_with("Bill date\n")
    assert date_line is not None
    document_date = _extract_date(date_line)

    return NameComponents(document_date, "Thames Water", account_holder_name, "Bill")


@pdfrenamer
def bill_2023(document: pdf_document.Document) -> NameComponents | None:
    text_boxes = document[1]
    if not text_boxes:
        return None

    if not any("thameswater.co.uk/myaccount\n" in box for box in text_boxes):
        return None

    # 2022 bills have the address as first box.
    if not text_boxes[0].startswith("Page 1 of "):
        return None

    if "Your latest bill\n" not in text_boxes:
        return None

    latest_bill_idx = text_boxes.index("Your latest bill\n")

    account_holder_name = extract_account_holder_from_address(
        text_boxes[latest_bill_idx - 1]
    )

    date_line = text_boxes.find_box_starting_with("Bill date\n")
    assert date_line is not None
    document_date = _extract_date(date_line)

    return NameComponents(document_date, "Thames Water", account_holder_name, "Bill")


@pdfrenamer
def letter(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("thameswater.letter")
    text_boxes = document[1]

    if "Thames Water Utilities Limited," not in text_boxes[-1]:
        return None

    date_line = text_boxes.find_box_starting_with("Date\n")
    if not date_line:
        return None

    logger.debug(f"found date line: {date_line!r}")
    document_date = _extract_date(date_line)

    account_holder_name = extract_account_holder_from_address(text_boxes[0])

    return NameComponents(document_date, "Thames Water", account_holder_name, "Letter")
