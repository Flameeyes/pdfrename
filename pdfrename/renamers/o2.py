# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, extract_account_holder_from_address


@pdfrenamer
def bill(document: pdf_document.Document) -> NameComponents | None:
    text_boxes = document[1]

    if (
        len(text_boxes) < 2
        or "Telefónica UK Limited" not in text_boxes[-1]
        or text_boxes[0] != "Copy Bill\n"
    ):
        return None

    fields_box_index = text_boxes.find_index_starting_with("Account number\n")
    assert fields_box_index is not None

    bill_info = build_dict_from_fake_table(
        text_boxes[fields_box_index], text_boxes[fields_box_index + 1]
    )
    bill_date = dateparser.parse(bill_info["Bill date"], languages=["en"])
    assert bill_date is not None

    # Older bills have the fake table first, followed the address; newer bills use
    # a more complicated format, but the address is on the second box.
    if fields_box_index == 1:
        address_box = text_boxes[3]
    else:
        address_box = text_boxes[1]

    account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(
        bill_date,
        "O2 UK",
        account_holder_name,
        "Bill",
    )
