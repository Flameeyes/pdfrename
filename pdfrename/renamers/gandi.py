# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re

import dateparser
from more_itertools import one

from ..doctypes.en import INVOICE
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:

    if not (first_page := document[1]):
        return None

    if not first_page[0].startswith("From:\nGandi International\n"):
        return None

    invoice_number_box = first_page.find_box_starting_with("Invoice N° ")
    assert invoice_number_box is not None
    invoice_number = invoice_number_box.removeprefix("Invoice N° ").strip()

    date_match = one(
        first_page.find_all_matching_regex(
            re.compile(r"(?:.*\n)?Status: .*\nDate: ([^\n]+)\n")
        )
    )
    date = dateparser.parse(date_match.group(1), languages=["en"])
    assert date is not None

    account_holder_box = first_page.find_box_starting_with("To:\n")
    assert account_holder_box is not None
    account_holder = account_holder_box.split("\n")[1]

    return NameComponents(
        date=date,
        service_name="Gandi",
        account_holder=(account_holder,),
        document_type=INVOICE,
        document_number=invoice_number,
    )
