# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

from components import NameComponents


def try_azure(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("azure")

    is_azure = any("Microsoft Ireland Operations Ltd" in box for box in text_boxes)
    if is_azure:
        logger.debug("Found Azure Invoice")

        address_idx = text_boxes.index("Bill to\n")
        address_str = text_boxes[address_idx + 1].strip()
        account_holder_name = address_str.split("\n")[-1].split(":", 1)[1]

        invoice_date_str = text_boxes[address_idx + 2]
        invoice_date = datetime.datetime.strptime(invoice_date_str, "%m/%d/%Y\n")
        assert invoice_date is not None

        return NameComponents(invoice_date, "Azure", account_holder_name, "Invoice")
