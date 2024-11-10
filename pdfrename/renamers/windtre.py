# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re
from datetime import datetime

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address


def _wind_or_windtre(box: str) -> bool:
    return box.startswith("Wind Telecomunicazioni S.p.A. - ")


@pdfrenamer
def bolletta_2006(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if not first_page.find_box_with_match(_wind_or_windtre):
        return None

    if first_page[0] != "CONTO\nTELEFONICO\n":
        return None

    invoice_number_box = first_page.find_box_starting_with("Numero Fattura\n")
    invoice_date_box = first_page.find_box_starting_with("Data emissione fattura")
    if invoice_number_box is None or invoice_date_box is None:
        return None

    account_holder_idx = first_page.index("Intestatario\n") + 1
    invoice_number = invoice_number_box.split("\n")[1]
    invoice_date_string = invoice_date_box.split("\n")[1]
    invoice_date = datetime.strptime(invoice_date_string, "%d/%m/%Y")

    account_holder = extract_account_holder_from_address(first_page[account_holder_idx])
    if not (
        account_number_match := re.search(
            r"\nCod\. Cliente:  ([0-9]+)\n", first_page[account_holder_idx]
        )
    ):
        return None

    return NameComponents(
        invoice_date,
        "Wind",
        account_holder,
        "Bolletta",
        account_number=account_number_match.group(1),
        document_number=invoice_number,
    )
