# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import datetime
from typing import Optional

from ..lib.renamer import NameComponents, pdfrenamer


@pdfrenamer
def invoice(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("azure.invoice")

    is_azure = any("Microsoft Ireland Operations Ltd" in box for box in text_boxes)
    if not is_azure:
        return None

    logger.debug("Found Azure Invoice")

    address_idx = text_boxes.index("Bill to\n")
    address_str = text_boxes[address_idx + 1].strip()
    account_holder_name = address_str.split("\n")[-1].split(":", 1)[1]

    for box in text_boxes:
        try:
            invoice_date = datetime.datetime.strptime(box, "%m/%d/%Y\n")
            logger.debug(f"Found an invoice date line {invoice_date!r}")
            break
        except ValueError:
            continue
    else:
        raise Exception("No invoice date found")

    return NameComponents(invoice_date, "Azure", account_holder_name, "Invoice")
