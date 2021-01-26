# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dateparser
import re

from typing import Optional

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .utils import (
    find_box_starting_with,
)


@pdfrenamer
def statement(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("ms_bank.statement")

    if "M&S Bank" not in text_boxes[-1]:
        return None

    account_name_box = find_box_starting_with(text_boxes, "Account Name\n")
    assert account_name_box

    account_holder_name = account_name_box.split("\n")[1].strip()

    # The statement period is just before the account name box.
    period_box_index = text_boxes.index(account_name_box) - 1
    period_line = text_boxes[period_box_index]

    logger.debug(f"found period specification {period_line!r}")

    period_match = re.search(
        r"^[0-9]{2} [A-Z][a-z]+(?: [0-9]{4})? to ([0-9]{2} [A-Z][a-z]+ [0-9]{4})\n$",
        period_line,
    )
    assert period_match

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    return NameComponents(
        statement_date,
        "M&S Bank",
        account_holder_name,
        "Statement",
    )
