# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import re
import dateparser

from typing import Optional

from components import NameComponents
from utils import (
    extract_account_holder_from_address,
    find_box_starting_with,
)


def try_vodafone(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("vodafone")

    is_vodafone = any(
        "\nRegistered address: Vodafone Limited, " in box for box in text_boxes
    )

    if is_vodafone:
        account_holder_name = extract_account_holder_from_address(text_boxes[3])

        date_match = re.match(r"^([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})", text_boxes[0])
        assert date_match

        bill_date = dateparser.parse(date_match.group(1), languages=["en"])
        assert bill_date is not None

        return NameComponents(bill_date, "Vodafone", account_holder_name, "Bill")
