# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import logging

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("google.invoice")
    text_boxes = document[1]

    is_google = any("Google Commerce Limited\n" in box for box in text_boxes)
    if not is_google:
        return None

    logger.debug("This is a Google invoice.")

    address_idx = text_boxes.index("Bill to\n")
    account_holder_name = text_boxes[address_idx + 1].strip()

    invoice_number_box = text_boxes.find_box_starting_with("Invoice number\n")
    assert invoice_number_box
    match invoice_number_box.count("\n"):
        case 2:
            invoice_number_idx = text_boxes.index(invoice_number_box) + 1
            invoice_number = text_boxes[invoice_number_idx].strip()
        case 3:
            invoice_number = invoice_number_box.split("\n")[2]

    invoice_date_box = text_boxes.find_box_starting_with("Invoice date\n")
    assert invoice_date_box
    match invoice_date_box.count("\n"):
        case 2:
            invoice_date_idx = text_boxes.index(invoice_date_box) + 1
            invoice_date_str = text_boxes[invoice_date_idx]
        case 3:
            invoice_date_str = invoice_date_box.split("\n")[2]

    invoice_date = dateparser.parse(invoice_date_str, languages=["en"])
    assert invoice_date is not None

    return NameComponents(
        invoice_date,
        "Google",
        account_holder_name,
        "Invoice",
        document_number=invoice_number,
    )
