# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

from typing import Optional

import dateparser

from pdfrename.renamers.digikey import invoice

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address


@pdfrenamer
def mouser_invoice(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("mouser_invoice")

    if len(text_boxes) < 28:
        return None

    if "Mouser Part Number\n" not in text_boxes[27]:
        return None

    account_holder_name_str = text_boxes[26]
    logger.debug(f"The name line is {account_holder_name_str!r}")

    account_holder_str = extract_account_holder_from_address(account_holder_name_str)

    account_holder_name = " ".join(reversed(account_holder_str.split(", ", 1)))

    invoice_date_box_idx = text_boxes.index("Invoice Date\n")
    invoice_date_str = text_boxes[invoice_date_box_idx + 3]

    logger.debug(f"Found an invoice date line {invoice_date_str!r}")
    invoice_date = dateparser.parse(invoice_date_str, languages=["en"])
    assert invoice_date

    return NameComponents(invoice_date, "Mouser", account_holder_name, "Invoice")
