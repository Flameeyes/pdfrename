# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

from typing import Optional

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address, find_box_starting_with


@pdfrenamer
def payslip_uk(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("facebook.payslip_uk")

    if len(text_boxes) < 5:
        return None

    if text_boxes[2] != "Facebook UK Ltd\n":
        return None

    logger.debug("Found Facebook Payslip")

    account_holder_name = extract_account_holder_from_address(text_boxes[1])

    date_box = find_box_starting_with(text_boxes, "Date : ")
    assert date_box is not None

    payslip_date = dateparser.parse(date_box[7:], languages=["en"])
    assert payslip_date is not None

    return NameComponents(payslip_date, "Facebook", account_holder_name, "Payslip")
