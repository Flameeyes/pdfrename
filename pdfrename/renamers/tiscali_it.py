# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer


@pdfrenamer
def fattura_aziendale_2010(document: pdf_document.Document) -> NameComponents | None:

    if not (first_page := document[1]):
        return None

    if not first_page.find_box_starting_with("Tiscali Italia S.p.A. con socio unico"):
        return None

    if not first_page[0].startswith("Servizio Clienti Aziende: 192 130\n"):
        return None

    account_holder_box = first_page.find_box_starting_with("Sede Legale:\n")
    assert account_holder_box is not None
    account_holder = account_holder_box.split("\n")[1]

    # We include the *contract* number as the account number, rather than the client
    # number, as the same client might have multiple invoices over the same time period.
    contract_number_box = first_page.find_box_starting_with("Codice Contratto\n")
    assert contract_number_box is not None
    contract_number = contract_number_box.split("\n")[1]

    document_number_box = first_page.find_box_starting_with("Fattura N°\n")
    assert document_number_box is not None
    document_number = document_number_box.split("\n")[1]

    date_box = first_page[first_page.index(document_number_box) + 1]
    date = datetime.datetime.strptime(date_box, "Del\n%d/%m/%Y\n")
    assert date is not None

    return NameComponents(
        date=date,
        service_name="Tiscali",
        account_holder=(account_holder,),
        document_type="Fattura",
        account_number=contract_number,
        document_number=document_number,
    )
