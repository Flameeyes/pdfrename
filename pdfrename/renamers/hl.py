# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

from more_itertools import one

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

    client_number_match = one(
        first_page.find_all_matching_regex(re.compile("Client number: ([0-9]+)\n"))
    )
    client_number_index = first_page.index(client_number_match.group(0))

    account_holder = first_page[client_number_index - 1].strip()

    return NameComponents(
        date,
        _HL_SERVICE,
        (account_holder,),
        "Active Savings Statement",
        account_number=client_number_match.group(1),
    )


@pdfrenamer
def investment_report(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if not first_page.find_box_starting_with(
        "Hargreaves Lansdown Asset Management Limited"
    ):
        return None

    if "Your investment report\n" not in first_page:
        return None

    # The date that is present in the document is just a month, so ignore that and get it from
    # the document creation date.
    if not (date := document.creation_date):
        return None

    client_number_match = one(
        first_page.find_all_matching_regex(
            re.compile(r"[A-Z][a-z]+ [0-9]{4}\nClient Number: ([0-9]+)\n")
        )
    )
    client_number_index = first_page.index(client_number_match.group(0))

    account_holder = extract_account_holder_from_address(
        first_page[client_number_index - 1]
    )

    return NameComponents(
        date,
        _HL_SERVICE,
        (account_holder,),
        "Investment Report",
        account_number=client_number_match.group(1),
    )


_CONTRACT_NOTE_ACCOUNTS = {
    "HL Fund & Share Account\n",
    "HL Lifetime ISA\n",
    "HL Stocks & Shares ISA\n",
}


@pdfrenamer
def contract_note(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    first_page_set = set(first_page)

    if (not first_page_set & _CONTRACT_NOTE_ACCOUNTS) or (
        b"FPDF" not in (document.producer or b"")
    ):
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
