# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("lloyds.statement")
    text_boxes = document[1]

    is_lloyds = any("logo, Lloyds Bank.\n" in box for box in text_boxes)

    if not is_lloyds:
        return None

    document_requestor = text_boxes.find_box_starting_with("Document requested by:\n")
    assert document_requestor

    account_holder_name = document_requestor.split("\n")[1]

    for box in text_boxes:
        date_match = re.search(
            r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}.\n)",
            box,
        )
        if date_match:
            break
    else:
        logger.debug("Unable to find the statement date.")

    assert date_match

    bill_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert bill_date is not None

    return NameComponents(bill_date, "Lloyds", account_holder_name, "Statement")
