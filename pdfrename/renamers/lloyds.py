# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
# SPDX-FileCopyrightText: 2026 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..doctypes.en import STATEMENT
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)

_ACCOUNT_NUMBER_REGEX = re.compile(r"(\d{2}-\d{2}-\d{2})\n(\d+)\n")


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("statement")
    text_boxes = document[1]

    # Identify service from logo
    service = None
    if any("logo, Lloyds Bank.\n" in box for box in text_boxes):
        service = "Lloyds"
    elif any("logo, Bank Of Scotland.\n" in box for box in text_boxes):
        service = "Bank of Scotland"
    else:
        return None

    logger.debug(f"Found likely {service} statement.")

    # Account holder
    document_requestor = text_boxes.find_box_starting_with("Document requested by:\n")
    assert document_requestor
    account_holder_name = document_requestor.split("\n")[1].strip()

    # Statement date
    date_match = None
    for box in text_boxes:
        date_match = re.search(
            r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}.\n)",
            box,
        )
        if date_match:
            break

    assert date_match, "Unable to find the statement date."
    bill_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert bill_date is not None

    # Account number – optional, present on both Lloyds and Bank of Scotland
    account_number = None
    if sort_code_box := text_boxes.find_box_starting_with("Sort Code\n"):
        idx = text_boxes.index(sort_code_box)
        if idx + 1 < len(text_boxes):
            value_box = text_boxes[idx + 1]
            account_match = _ACCOUNT_NUMBER_REGEX.search(value_box)
            if account_match:
                account_number = account_match.group(2)

    return NameComponents(
        bill_date,
        service,
        account_holder_name,
        STATEMENT,
        account_number=account_number,
    )
