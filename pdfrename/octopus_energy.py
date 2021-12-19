# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from typing import Optional

import dateparser

from .lib import pdf_document
from .lib.renamer import NameComponents, pdfrenamer
from .lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def statement(document: pdf_document.Document) -> Optional[NameComponents]:
    logger = _LOGGER.getChild("statement")

    try:
        first_page = document[1]
    except IndexError:
        return None

    if (
        not first_page.find_box_starting_with("Octopus Energy Limited\n")
        or "Your energy account\n" not in first_page
    ):
        return None

    logger.debug("Found likely Octopus Energy statement.")

    account_holder_name = extract_account_holder_from_address(first_page[0])

    bill_details = first_page[1]
    logger.debug(f"Found bill details: {bill_details!r}")

    date_match = re.search(
        "\nBill Reference: .+ \(([0-9]+[a-z]{2} [A-Z][a-z]{2}\. [0-9]{4})\)\n$",
        bill_details,
    )
    if not date_match:
        logger.debug("Failed to match date.")
        return None

    statement_date = dateparser.parse(date_match.group(1), languages=["en"])

    return NameComponents(
        statement_date, "Octopus Energy", account_holder_name, "Statement"
    )
