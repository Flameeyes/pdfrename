# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .lib import pdf_document


@pdfrenamer
def statement(document: pdf_document.Document) -> Optional[NameComponents]:
    text_boxes = document[1]  # Only need the first page.

    if text_boxes[0] != "www.americanexpress.co.uk\n":
        return None

    document_type = text_boxes[4].strip()
    if document_type == "Statement of Account":
        document_type = "Statement"

    account_holder_box = text_boxes.find_box_starting_with("Prepared for\n")
    assert account_holder_box
    account_holder_name = account_holder_box.split("\n")[1].strip().title()

    # The date is the box after the Membership Number. We can't look for the one starting
    # with "Date" because there's more than one.
    membership_index = text_boxes.find_index_starting_with("Membership Number\n")
    assert membership_index is not None

    date_box = text_boxes[membership_index + 1]
    date_fields = date_box.split("\n")
    assert date_fields[0] == "Date"

    statement_date = datetime.datetime.strptime(date_fields[1], "%d/%m/%y")

    return NameComponents(
        statement_date,
        "American Express",
        account_holder_name,
        "Statement",
    )
