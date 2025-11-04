# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
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
        "M&S Bank",
        account_holder_name,
        "Statement",
    )
