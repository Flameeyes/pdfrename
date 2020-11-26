# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import dateparser
import re

from typing import Optional

from components import NameComponents
from utils import extract_account_holder_from_address, find_box_starting_with


def try_ulster_bank(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("ulcer")

    if len(text_boxes) < 10:
        return None

    is_ulster_bank = any("www.ulsterbank.co.uk" in box for box in text_boxes)

    if is_ulster_bank:
        logger.debug("Found Ulster Bank Statement")
        account_holder_name = extract_account_holder_from_address(text_boxes[6])

        date_match = re.match(
            r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\n)",
            text_boxes[10],
        )
        assert date_match

        statement_date = dateparser.parse(date_match.group(1), languages=["en"])

        return NameComponents(
            statement_date, "Ulster Bank", account_holder_name, "Statement"
        )
