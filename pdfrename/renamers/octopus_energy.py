# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
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

    bill_details_index = first_page.find_index_starting_with("Your Account Number: ")
    assert bill_details_index is not None
    bill_details = first_page[bill_details_index]
    logger.debug(f"Found bill details: {bill_details!r}")

    account_holder_index = first_page.index("Your energy account\n") - 1
    # More recent (2025) statements appear to have moved things around a bit.
    if account_holder_index == bill_details_index:
        account_holder_index -= 1
    account_holder_name = extract_account_holder_from_address(
        first_page[account_holder_index]
    )

    date_match = re.search(
        r"\nBill Reference: .+ \(([0-9]+[a-z]{2}\s[A-Z][a-z.]{2,}\s[0-9]{4})\)\n$",
        bill_details,
    )
    if not date_match:
        logger.debug("Failed to match date.")
        return None

    statement_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert statement_date is not None

    return NameComponents(
        statement_date, "Octopus Energy", account_holder_name, "Statement"
    )
