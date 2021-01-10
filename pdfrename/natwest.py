# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import dateparser
import re

from typing import Optional

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .utils import extract_account_holder_from_address, find_box_starting_with

_WEBSITES_TO_BANK = {
    "www.ulsterbank.co.uk": "Ulster Bank (NI)",
    "www.natwest.com": "NatWest",
}


@pdfrenamer
def natwest_group_statement(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("natwest.natwest_group_statement")

    if text_boxes[0] != "Statement\n" or "Period\n" not in text_boxes:
        return None

    for website, bank_name in _WEBSITES_TO_BANK.items():
        if any(website in box for box in text_boxes):
            break
    else:
        return None

    logger.debug(f"Possible {bank_name} statement.")
    period_line_index = text_boxes.index("Period\n") + 1
    period_line = text_boxes[period_line_index]

    logger.debug(f"Found period line: {period_line!r}")

    date_match = re.match(
        r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\n)",
        period_line,
    )
    assert date_match
    statement_date = dateparser.parse(date_match.group(1), languages=["en"])

    # The account holder(s) as well as the account type follow the IBAN. Take the first
    # account holder for now, as we don't have a good format for multiple holders.
    iban_box = find_box_starting_with(text_boxes, "IBAN: ")
    assert iban_box
    account_holders_idx = text_boxes.index(iban_box) + 1
    account_holders_box = text_boxes[account_holders_idx]

    account_holder_name, _ = account_holders_box.split("\n", 1)

    return NameComponents(
        statement_date, bank_name, account_holder_name.title(), "Statement"
    )
