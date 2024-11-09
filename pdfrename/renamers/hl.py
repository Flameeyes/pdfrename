# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

_HL_SERVICE = "Hargreaves Lansdown"


@pdfrenamer
def tax_certificate(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if not first_page.find_box_starting_with(
        "Hargreaves Lansdown Asset Management Limited "
    ):
        return None

    if "Your tax certificate\n" not in first_page:
        return None

    if not (date := document.creation_date):
        return None

    account_holder = extract_account_holder_from_address(first_page[0])

    return NameComponents(
        date,
        _HL_SERVICE,
        (account_holder,),
        "Tax Certificate",
    )


@pdfrenamer
def savings_statement(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if not first_page.find_box_starting_with("Hargreaves Lansdown Savings Limited"):
        return None

    if "Account: Active Savings Account\n" not in first_page:
        return None

    if not (date := document.creation_date):
        return None

    client_number_index = first_page.find_index_starting_with("Client number: ")
    if not client_number_index:
        return None

    account_holder = first_page[client_number_index - 1].strip()

    return NameComponents(
        date,
        _HL_SERVICE,
        (account_holder,),
        "Active Savings Statement",
    )


_CONTRACT_NOTE_ACCOUNTS = {
    "HL Fund & Share Account\n",
    "HL Lifetime ISA\n",
    "HL Stock & Shares ISA\n",
}


@pdfrenamer
def contract_note(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    first_page_set = set(first_page)

    if (
        not first_page_set & _CONTRACT_NOTE_ACCOUNTS
    ) or b"FPDF" not in document.producer:
        return None

    if (
        instructions_idx := first_page.index("We have today on your instructions\n")
    ) is None:
        return None

    note_number = first_page[instructions_idx - 1].strip()
    account_holder = extract_account_holder_from_address(first_page[0])
    date = datetime.datetime.strptime(first_page[1], "%d/%m/%Y\n")

    return NameComponents(
        date,
        _HL_SERVICE,
        (account_holder,),
        "Contract Note",
        document_number=note_number,
    )
