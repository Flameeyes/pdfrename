# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address


@pdfrenamer
def statement(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("kbc.statement")

    is_kbc = any("ICONIE2D\n" in box for box in text_boxes)
    if not is_kbc:
        return None

    logger.debug("Found KBC Ireland")

    account_holder_name = extract_account_holder_from_address(text_boxes[0])

    statement_date = dateparser.parse(text_boxes[1], languages=["en"])

    assert statement_date is not None

    return NameComponents(statement_date, "KBC", account_holder_name, "Statement")
