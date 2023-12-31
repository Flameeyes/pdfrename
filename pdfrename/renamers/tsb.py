# SPDX-FileCopyrightText: 2023 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address


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

    return NameComponents(date, "TSB", name, "Statement")
