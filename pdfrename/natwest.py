# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from typing import Optional

import dateparser

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .lib import pdf_document

_LOGGER = logging.getLogger(__name__)

_WEBSITES_TO_BANK = {
    "www.ulsterbank.co.uk": "Ulster Bank (NI)",
    "www.natwest.com": "NatWest",
}


@pdfrenamer
def statement(document: pdf_document.Document) -> Optional[NameComponents]:
    logger = _LOGGER.getChild("statement")

    first_page = document[1]

    if not first_page or first_page[0] != "Statement\n" or "Period\n" not in first_page:
        return None

    for website, bank_name in _WEBSITES_TO_BANK.items():
        if any(website in box for box in first_page):
            break
    else:
        return None

    logger.debug(f"Possible {bank_name} statement.")
    period_line_index = first_page.index("Period\n") + 1
    period_line = first_page[period_line_index]

    logger.debug(f"Found period line: {period_line!r}")

    date_match = re.match(
        r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\n)",
        period_line,
    )
    assert date_match
    statement_date = dateparser.parse(date_match.group(1), languages=["en"])

    # The account holder(s) as well as the account type follow the IBAN, either in the same
    # or in different boxes.
    # Take the first account holder for now, as we don't have a good format for multiple
    # holders.
    iban_box_index = first_page.find_index_starting_with("IBAN: ")
    assert iban_box_index != None

    # If the following box says "Branch Details" then the details are attached to the IBAN
    # box.
    account_holders_string = first_page[iban_box_index + 1]
    if account_holders_string == "Branch Details\n":
        # Extract the account holder from the IBAN box. There's more lines on it, which
        # represent multiple holders, and the account time (e.g. Reward). Ignore them.
        account_holder_name = first_page[iban_box_index].split("\n", 2)[1]
    else:
        account_holder_name, _ = account_holders_string.split("\n", 1)

    return NameComponents(
        statement_date, bank_name, account_holder_name.title(), "Statement"
    )
