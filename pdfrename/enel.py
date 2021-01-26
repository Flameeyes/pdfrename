# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .utils import (
    find_box_starting_with,
    extract_account_holder_from_address,
)


@pdfrenamer
def bill(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("enel.bill")

    enel_address_box = find_box_starting_with(
        text_boxes, "Enel Energia - Mercato libero dell'energia\n"
    )
    if not enel_address_box:
        return None
    enel_address_index = text_boxes.index(enel_address_box)

    # Late 2019: the ENEL address is at the beginning, the address is two boxes before the
    # payment due date.
    due_date_box = find_box_starting_with(text_boxes, "Entro il ")
    assert due_date_box

    address_box_index = text_boxes.index(due_date_box) - 2
    address_box = text_boxes[address_box_index]

    # In 2020: the account holder address is _before_ the ENEL address. We can tell if we
    # got the wrong address box if it's too short in lines.
    if address_box.count("\n") < 2:
        address_box_index = enel_address_index - 1
        address_box = text_boxes[address_box_index]

    account_holder_name = extract_account_holder_from_address(address_box)

    # In 2018, the address was before the customer number instead, try again.
    if account_holder_name == "Periodo":
        customer_id_box = find_box_starting_with(text_boxes, "N° CLIENTE\n")
        assert customer_id_box
        customer_id_box_index = text_boxes.index(customer_id_box)

        address_box = text_boxes[customer_id_box_index - 1]
        account_holder_name = extract_account_holder_from_address(address_box)

    # The date follows the invoice number, look for the invoce number, then take the next.
    invoice_number_box = find_box_starting_with(text_boxes, "N. Fattura ")
    assert invoice_number_box

    date_box_index = text_boxes.index(invoice_number_box) + 1
    date_box = text_boxes[date_box_index]

    bill_date = datetime.datetime.strptime(date_box, "Del %d/%m/%Y\n")

    return NameComponents(
        bill_date,
        "ENEL Energia",
        account_holder_name,
        "Bolletta",
    )
