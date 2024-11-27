# SPDX-FileCopyrightText: 2023 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
from typing import Final

import dateparser

from ..doctypes.en import STATEMENT, STATEMENT_OF_FEES
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_TSB_SERVICE: Final[str] = "TSB Bank"


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    text_boxes = document[1]
    if not text_boxes or "www.tsb.co.uk\n" not in text_boxes:
        return None

    # The date follows the IBAN.
    iban_index = text_boxes.find_index_starting_with("IBAN: ")
    assert iban_index is not None

    date_str = text_boxes[iban_index + 1]
    date = datetime.datetime.strptime(date_str, "%d/%m/%Y\n")

    # Address box is the first box on the page.
    name = extract_account_holder_from_address(text_boxes[0])

    return NameComponents(date, _TSB_SERVICE, name, STATEMENT)


@pdfrenamer
def statement_of_fees(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if not first_page:
        return None

    if not first_page.find_box_starting_with("TSB Bank plc Registered Office:"):
        return None

    if not first_page[0] == "Statement of Fees\n":
        return None

    # Ignore the PDF creation date, it's when the document was downloaded.
    # Instead look for the date after the period identification.
    # This is almost the same as Natwest's
    period_line_idx = first_page.find_index_starting_with("From: ")
    assert period_line_idx is not None
    date_string = first_page[period_line_idx + 1]

    date = dateparser.parse(date_string, languages=["en"])
    assert date is not None

    account_label_index = first_page.index("Account\n")
    account_holder = extract_account_holder_from_address(
        first_page[account_label_index - 1]
    )

    return NameComponents(
        date,
        _TSB_SERVICE,
        (account_holder,),
        STATEMENT_OF_FEES,
    )
