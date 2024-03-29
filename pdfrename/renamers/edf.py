# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import re

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address, find_box_starting_with


@pdfrenamer
def bill(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("edf.bill")

    is_edf = any("edfenergy.com\n" in box for box in text_boxes)
    if not is_edf:
        return None

    logger.debug("This is EDF Energy bill.")

    account_holder_name = extract_account_holder_from_address(text_boxes[2])

    edf_statement_period_line = find_box_starting_with(text_boxes, "Bill date:")
    if not edf_statement_period_line:
        return None

    logger.debug(f"Found EDF Energy bill period line {edf_statement_period_line!r}")

    period_match = re.match(
        r"^Bill date: ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n",
        edf_statement_period_line,
    )
    assert period_match
    bill_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert bill_date

    return NameComponents(bill_date, "EDF Energy", account_holder_name, "Bill")
