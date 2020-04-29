# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re
from typing import Optional

import dateparser

from components import NameComponents
from utils import find_box_starting_with


def try_scaleway(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("scaleway")

    if not find_box_starting_with(text_boxes, "Online SAS,"):
        return None

    customer_box = find_box_starting_with(text_boxes, "Customer \n")
    if customer_box:
        # Latest template
        account_holder = customer_box.split("\n")[1].strip()
    else:
        # Previous templates split this into two separate boxes.
        customer_label_idx = text_boxes.index("Customer\n")
        customer_box = text_boxes[customer_label_idx + 1]
        account_holder = customer_box.strip()

    date_box = find_box_starting_with(text_boxes, "Issued: \n")
    if date_box:
        # Latest template
        date_str = date_box.split("\n")[1].strip()
    else:
        # We need to find teh Issued line that is mixed together with other items, so just
        # use regex to find it.
        for box in text_boxes:
            # We don't really use a strict regex here, but we do only extract the _date_
            # part rather than the time, which is also present but useless to the
            # renaming.
            date_match = re.search(
                r"Issued: ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}) at [0-9]", box
            )
            if date_match:
                break
        else:
            logger.debug("Unable to find the invoice issue date.")

        assert date_match
        date_str = date_match.group(1)

    bill_date = dateparser.parse(date_str)

    return NameComponents(bill_date, "Scaleway", account_holder, "Invoice")
