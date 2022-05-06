# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import re
from typing import Optional

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address, find_box_starting_with


@pdfrenamer
def invoice(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("digikey.invoice")

    if len(text_boxes) < 2:
        return None

    is_digikey = "www.digikey." in text_boxes[1]

    if not is_digikey:
        return None

    # Looking for a stray 'i' from the 'Ship To' label.
    account_holder_name_idx = text_boxes.index("i\n")
    account_holder_name_str = text_boxes[account_holder_name_idx + 1]
    logger.debug(f"The name line is {account_holder_name_str!r}")

    account_holder_name = extract_account_holder_from_address(account_holder_name_str)

    invoice_date_line = find_box_starting_with(text_boxes, "Invoice Date:\n")
    assert invoice_date_line

    logger.debug(f"Found an invoice date line {invoice_date_line!r}")
    date_match = re.search(
        r"^Invoice Date:\n([0-9]{1,2}-[A-Z][a-z]{2,}-[0-9]{4}\n)", invoice_date_line
    )
    assert date_match is not None

    invoice_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert invoice_date is not None

    return NameComponents(invoice_date, "Digikey", account_holder_name, "Invoice")
