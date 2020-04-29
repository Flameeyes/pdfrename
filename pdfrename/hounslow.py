# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re
from typing import Optional, Sequence

import dateparser

from components import NameComponents
from utils import (
    drop_honorific,
    extract_account_holder_from_address,
    find_box_starting_with,
)


def try_hounslow(text_boxes: Sequence[str], parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("hounslow")

    if not find_box_starting_with(text_boxes, "London Borough of Hounslow\n"):
        return None

    subject = text_boxes[2]
    if not subject.startswith("Council Tax Bill "):
        logger.debug("Not a council tax bill, unknown format.")
        return None

    bill_date = dateparser.parse(text_boxes[0], languages=["en"])

    # In older bills, the subject box includes the address.
    if subject.count("\n") > 1:
        address_box = subject.split("\n", 1)[1]
    else:
        address_box = text_boxes[3]

    account_holder = extract_account_holder_from_address(address_box)
    # There can be more than one account holder, which makes things a bit more complicated.
    if "&" in account_holder:
        account_holders = [
            drop_honorific(holder.strip()) for holder in account_holder.split("&")
        ]

        account_holder = ", ".join(account_holders)

    return NameComponents(bill_date, "LB Hounslow", account_holder, "Council Tax Bill",)
