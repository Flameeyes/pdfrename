# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import re
from typing import Optional

import dateparser

from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import (
    build_dict_from_fake_table,
    extract_account_holder_from_address,
    find_box_starting_with,
)


@pdfrenamer
def tesco_bank(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("tesco_bank")

    # Before checking for statements, check other communications.
    if text_boxes[0].startswith("Tesco Bank\n") and find_box_starting_with(
        text_boxes, "Annual Summary of Interest\n"
    ):
        assert "Minicom:" in text_boxes[2]

        account_holder_name = text_boxes[4].strip()
        tax_year_line = find_box_starting_with(text_boxes, "Tax Year:")

        tax_year_match = re.search(
            r"^Tax Year: [0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n$",
            tax_year_line,
        )
        assert tax_year_match

        document_date = dateparser.parse(tax_year_match.group(1))

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

    return NameComponents(
        statement_date,
        "Tesco Bank",
        account_holder_name,
        document_type,
    )
