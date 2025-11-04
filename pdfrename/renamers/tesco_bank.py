# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, extract_account_holder_from_address


@pdfrenamer
def tesco_bank(document: pdf_document.Document) -> NameComponents | None:
    text_boxes = document[1]
    # Before checking for statements, check other communications.
    if text_boxes[0].startswith("Tesco Bank\n") and (
        metadata := text_boxes.find_box_starting_with("Annual Summary of Interest\n")
    ):
        assert "Minicom:" in text_boxes[2]

        metadata_idx = text_boxes.index(metadata)

        account_holder_name = text_boxes[metadata_idx - 2].strip()
        tax_year_line = text_boxes.find_box_starting_with("Tax Year:")
        assert tax_year_line is not None

        tax_year_match = re.search(
            r"^Tax Year: [0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n$",
            tax_year_line,
        )
        assert tax_year_match

        document_date = dateparser.parse(tax_year_match.group(1))
        assert document_date is not None

        return NameComponents(
            document_date,
            "Tesco Bank",
            account_holder_name,
            "Annual Summary of Interest",
        )

    if not any("tescobank.com/mmc" in box for box in text_boxes):
        return None

    assert "Current Account\n" in text_boxes[0]

    if text_boxes[1] == "Monthly statement\n":
        document_type = "Statement"
    else:
        document_type = text_boxes[1].strip().title()

    account_holder_name = extract_account_holder_from_address(text_boxes[2])

    fields_box = text_boxes[3]
    values_box = text_boxes[4]

    statement_info = build_dict_from_fake_table(fields_box, values_box)

    statement_date = dateparser.parse(
        statement_info["Statement date:"], languages=["en"]
    )
    assert statement_date is not None

    return NameComponents(
        statement_date,
        "Tesco Bank",
        account_holder_name,
        document_type,
    )
