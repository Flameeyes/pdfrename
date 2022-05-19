# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    text_boxes = document[1]  # Only need the first page.

    if len(text_boxes) < 4:
        return None

    if text_boxes[0] == "www.americanexpress.co.uk\n":
        document_type = text_boxes[4].strip()
    elif text_boxes[0] == "americanexpress.co.uk\n":
        document_type = text_boxes[3].strip()
    elif text_boxes[3] == "americanexpress.co.uk\n":
        document_type = text_boxes[0].strip()
    else:
        return None

    if document_type == "Statement of Account":
        document_type = "Statement"

    account_holder_box = text_boxes.find_box_starting_with("Prepared for\n")
    assert account_holder_box
    account_holder_name = account_holder_box.split("\n")[1].strip()

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
