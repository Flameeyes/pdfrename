# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re
from typing import Optional, Sequence

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, find_box_starting_with


@pdfrenamer
def invoice(text_boxes: Sequence[str], parent_logger) -> Optional[NameComponents]:

    is_aws = find_box_starting_with(text_boxes, "Amazon Web Services, Inc. Invoice\n")
    if not is_aws:
        is_aws = find_box_starting_with(text_boxes, "Amazon Web Services Invoice\n")

    if not is_aws:
        return None

    fields_box = find_box_starting_with(text_boxes, "Invoice Number:\n")
    assert fields_box
    fields_index = text_boxes.index(fields_box)

    # There's at least two versions of this, where the fields are either right after, or
    # once more after that. Try both.
    values_box = text_boxes[fields_index + 1]
    if fields_box.count("\n") != values_box.count("\n"):
        values_box = text_boxes[fields_index + 2]

    invoice_info = build_dict_from_fake_table(fields_box, values_box)

    invoice_date = dateparser.parse(invoice_info["Invoice Date:"], languages=["en"])

    address_box = find_box_starting_with(text_boxes, "Bill to Address:\n")
    assert address_box

    account_holder = address_box.split("\n")[1]
    assert account_holder.startswith("ATTN: ")

    account_holder = account_holder[6:]  # Drop the ATTN

    return NameComponents(invoice_date, "AWS", account_holder, "Invoice")
