# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import dateparser
import re

from typing import Optional

from components import NameComponents
from utils import extract_account_holder_from_address, find_box_starting_with

_DOCUMENT_TYPES = {
    "Hello, here is your final bill.\n": "Final Bill",
    "Hello, here is your statement.\n": "Statement",
}


def try_soenergy(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("soenergy")

    if "www.so.energy\n" in text_boxes:

        for subject, document_type in _DOCUMENT_TYPES.items():
            if subject in text_boxes:
                break
        else:
            logger.debug(f"Unknown document type. Subject: {text_boxes!r}")
            return None

        subject_index = text_boxes.index(subject)

        # Find the account holder name at the start of the PDF.
        address_box = text_boxes[0]
        account_holder_name = extract_account_holder_from_address(address_box)

        period_line = text_boxes[subject_index + 1]
        logger.debug(f"found period specification: {period_line!r}")
        period_match = re.match(
            r"^For the period of [0-9]{1,2} [A-Z][a-z]{2} [0-9]{4} - ([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})\n$",
            period_line,
        )
        assert period_match
        statement_date = dateparser.parse(period_match.group(1), languages=["en"])

        return NameComponents(
            statement_date,
            "So Energy",
            account_holder_name,
            document_type,
        )

    annual_electricity_summary_period_line = find_box_starting_with(
        text_boxes, "Your annual electricity\nsummary\n"
    )

    if annual_electricity_summary_period_line:
        logger.debug(
            f"Found annual electricity summary period line {annual_electricity_summary_period_line!r}"
        )

        account_holder_name = extract_account_holder_from_address(text_boxes[0])

        date_match = re.match(
            r"^Your annual electricity\nsummary\nFor the period [0-9]{1,2} [A-Z][a-z]+ [0-9]{4} - ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n",
            annual_electricity_summary_period_line,
        )
        assert date_match

        statement_date = dateparser.parse(date_match.group(1), languages=["en"])
        assert statement_date is not None

        return NameComponents(
            statement_date, "So Energy", account_holder_name, "Annual Summary"
        )
