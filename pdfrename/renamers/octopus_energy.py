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

_OCTOPUS_PLATFORM_COMPANIES = (
    ("Octopus Energy Limited\n", "Octopus Energy"),
    ("E.ON Next Energy Limited", "E.ON Next"),
)

# Different companies use ever so slightly different templates.
# Find the first match.
_BILL_DETAILS_REGEXES = (
    re.compile(
        r"Your Account Number: (?P<account_number>[A-Z0-9\-]+)\n"
        r"Bill Reference: (?P<bill_number>[0-9]+)"
        r" \((?P<bill_date>[0-9]+[a-z]{2}\s[A-Z][a-z.]{2,}\s[0-9]{4})\)\n$",
    ),
    re.compile(
        r"Your account number: (?P<account_number>[A-Z0-9\-]+)\n"
        r"Bill reference: (?P<bill_number>[0-9]+)\n"
        r"Date: (?P<bill_date>[0-9]+\s[A-Z][a-z.]{2,}\s[0-9]{4})\n$"
    ),
)


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("statement")

    # So, Octopus Energy sells their billing platform to other suppliers
    # which means we're looking for statements that are generated with
    # their software, rather than specifically *their* bills.
    if b"octopusenergy-" not in document.producer:
        return None

    try:
        first_page = document[1]
    except IndexError:
        return None

    # Now look for which company it might be.
    for formal_name, correspondent_name in _OCTOPUS_PLATFORM_COMPANIES:
        if first_page.find_box_starting_with(formal_name) is not None:
            break
    else:
        logger.warning(
            "Found a statement from an Octopus platform, but from an unknown company!"
        )
        return None

    logger.debug(f"Found likely {correspondent_name} statement.")

    bill_details_index = first_page.find_index_starting_with(
        "Your Account Number: "
    ) or first_page.find_index_starting_with("Your account number: ")
    assert bill_details_index is not None
    bill_details = first_page[bill_details_index]
    logger.debug(f"Found bill details: {bill_details!r}")

    # It looks like 2025 has seen multiple statement templates, but for all of them,
    # the bill details are right after the account holder address.
    if bill_details_index == 1 or "Your energy account\n" not in first_page:
        account_holder_index = 0
    else:
        account_holder_index = first_page.index("Your energy account\n") - 1
        if account_holder_index == bill_details_index:
            account_holder_index -= 1

    account_holder_name = extract_account_holder_from_address(
        first_page[account_holder_index]
    )

    for bill_details_re in _BILL_DETAILS_REGEXES:
        if bill_details_match := bill_details_re.search(bill_details):
            break
    else:
        logger.warning("Failed to match bill details.")
        return None

    statement_date = dateparser.parse(
        bill_details_match.group("bill_date"), languages=["en"]
    )
    assert statement_date is not None

    return NameComponents(
        statement_date,
        correspondent_name,
        account_holder_name,
        "Statement",
        account_number=bill_details_match.group("account_number"),
        document_number=bill_details_match.group("bill_number"),
    )
