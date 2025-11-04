# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import logging

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("kbc.statement")
    text_boxes = document[1]

    is_kbc = any("ICONIE2D\n" in box for box in text_boxes)
    if not is_kbc:
        return None

    logger.debug("Found KBC Ireland")

    account_holder_name = extract_account_holder_from_address(text_boxes[0])

    statement_date = dateparser.parse(text_boxes[1], languages=["en"])

    assert statement_date is not None

    return NameComponents(statement_date, "KBC", account_holder_name, "Statement")
