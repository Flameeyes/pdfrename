# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import dateparser

from typing import Optional

from components import NameComponents
from utils import extract_account_holder_from_address


def try_mouser(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("mouser")

    is_mouser = "Mouser Part Number\n" in text_boxes[27]

    if is_mouser:
        account_holder_name_str = text_boxes[26]
        logger.debug(f"The name line is {account_holder_name_str!r}")

        account_holder_str = extract_account_holder_from_address(
            account_holder_name_str
        )

        account_holder_name = " ".join(reversed(account_holder_str.split(", ", 1)))

        invoice_date_box_idx = text_boxes.index("Invoice Date\n")
        invoice_date_str = text_boxes[invoice_date_box_idx + 3]

        logger.debug(f"Found an invoice date line {invoice_date_str!r}")
        invoice_date = dateparser.parse(invoice_date_str, languages=["en"])

        return NameComponents(invoice_date, "Mouser", account_holder_name, "Invoice")
