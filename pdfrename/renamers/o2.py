# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from typing import Optional

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, extract_account_holder_from_address


@pdfrenamer
def bill(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("o2.bill")

    if "Telefónica UK Limited" not in text_boxes[-1]:
        return None

    assert text_boxes[0] == "Copy Bill\n"

    fields_box = text_boxes[1]
    values_box = text_boxes[2]

    bill_info = build_dict_from_fake_table(fields_box, values_box)
    bill_date = dateparser.parse(bill_info["Bill date"], languages=["en"])
    assert bill_date is not None

    address_box = text_boxes[3]
    account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(
        bill_date,
        "O2 UK",
        account_holder_name,
        "Bill",
    )
