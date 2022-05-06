# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re
from typing import Optional, Sequence

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address, find_box_starting_with


@pdfrenamer
def statement(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("chase.statement")

    if not find_box_starting_with(text_boxes, "JPMorgan Chase Bank, N.A.\n"):
        return None

    # Period line changes from statement to statement, so try fuzzy-matching it instead.
    # Note that some more recent statements appear to have spacing issues, so we can't
    # match the space both sides.

    for box in text_boxes:
        period_match = re.search(
            r"^[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4} ?through ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})\n",
            box,
        )
        if period_match:
            break
    else:
        logger.debug("unable to find period line")
        return None

    assert period_match
    logger.debug(f"found period specification: {period_match.group(0)!r}")

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])
    assert statement_date

    # We anchor the address on the contact numbers on the side, but that's not working for
    # older statements.
    deaf_contact_box = find_box_starting_with(text_boxes, "Deaf and Hard of Hearing: ")
    if deaf_contact_box:
        deaf_contact_index = text_boxes.index(deaf_contact_box)

        account_holder_box = text_boxes[deaf_contact_index + 1]
        account_holder_name = account_holder_box.strip().title()
    else:
        # If we couldn't find the account holder through the contact number, it probably is a newer version of the template.
        # We can find the address box based on the period line instead.
        period_box = find_box_starting_with(text_boxes, period_match.group(0))
        address_box_index = text_boxes.index(period_box) - 1
        address_box = text_boxes[address_box_index]
        if address_box.count("\n") < 2:
            logger.debug("unable to find the account holder name")
            return None

        # Here's another corner case: when the statement has communications attached in
        # the first page, the mail routing number is attached to the address. So instead,
        # we need to drop that ourselves.
        if re.search(r"^[0-9]+ [A-Z]+ ", address_box):
            address_box = address_box.split("\n", 1)[1]

        account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(
        statement_date,
        "Chase",
        account_holder_name,
        "Statement",
    )
