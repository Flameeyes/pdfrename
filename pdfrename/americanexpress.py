# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .utils import find_box_starting_with


@pdfrenamer
def statement(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("americanexpress.statement")

    if text_boxes[0] != "www.americanexpress.co.uk\n":
        return None

    document_type = text_boxes[4].strip()
    if document_type == "Statement of Account":
        document_type = "Statement"

    account_holder_box = find_box_starting_with(text_boxes, "Prepared for\n")
    assert account_holder_box
    account_holder_index = text_boxes.index(account_holder_box)
    account_holder_name = account_holder_box.split("\n")[1].strip().title()

    # The date is the box after the Membership Number. We can't look for the one starting
    # with "Date" because there's more than one.
    membership_box = find_box_starting_with(text_boxes, "Membership Number\n")
    assert membership_box
    membership_index = text_boxes.index(membership_box)

    date_box = text_boxes[membership_index + 1]
    date_fields = date_box.split("\n")
    assert date_fields[0] == "Date"

    statement_date = datetime.datetime.strptime(date_fields[1], "%d/%m/%y")

    return NameComponents(
        statement_date,
        "American Express",
        account_holder_name,
        "Statement",
    )
