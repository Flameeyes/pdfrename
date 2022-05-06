# SPDX-FileCopyrightText: 2022 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer


@pdfrenamer
def financial_statement(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if "eBay S.à r.l.\n" not in first_page or "Financial statement\n" not in first_page:
        return None

    date_box = first_page.find_box_starting_with("Generated: ")
    assert date_box
    _, date_str = date_box.split(" ", 1)

    date = dateparser.parse(date_str, languages=["en"])
    assert date

    seller_name_label_idx = first_page.index("Seller name\n")
    seller_name = first_page[seller_name_label_idx + 1]

    # There's no difference on the first page of the document between the detailed and
    # summarized statements. There is a "1 of X" string, but it's actually harder to find
    # than just checking if there are more pages.
    try:
        document[2]
        document_type = "Detailed Statement"
    except IndexError:
        document_type = "Statement"

    return NameComponents(date, "eBay", seller_name, document_type)
