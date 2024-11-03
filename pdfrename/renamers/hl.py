# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging

from ..lib import pdf_document
from ..lib.itext import creation_date
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

    account_holder = extract_account_holder_from_address(first_page[0])

    return NameComponents(
        creation_date(document),
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

    client_number_index = first_page.find_index_starting_with("Client number: ")
    if not client_number_index:
        return None

    account_holder = first_page[client_number_index - 1].strip()

    return NameComponents(
        creation_date(document),
        _HL_SERVICE,
        (account_holder,),
        "Active Savings Statement",
    )
