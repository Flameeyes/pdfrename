# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT
import logging
from datetime import datetime

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

_HETZNER_SERVICE = "Hetzner"


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if len(first_page) < 3:
        return None

    if not first_page[0].startswith("Hetzner Online GmbH • "):
        return None

    account_holder = extract_account_holder_from_address(first_page[1])

    if not (invoice_date_str := first_page.find_box_starting_with("Invoice date: ")):
        return None

    invoice_date = datetime.strptime(invoice_date_str, "Invoice date: %d/%m/%Y\n")

    return NameComponents(invoice_date, _HETZNER_SERVICE, account_holder, "Invoice")
