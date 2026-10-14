# SPDX-FileCopyrightText: 2026 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from datetime import datetime

from ..doctypes.en import STATEMENT
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)

_SERVICE = "Zopa Bank"
_ACCOUNT_DETAILS_IDENTIFIER = "Account details\n"
_ACCOUNT_NUMBER_LABEL = "Account number\n"

_DATE_RANGE_RE = re.compile(
    r"^Your bank account statement for (?P<start_date>\d{2} [A-Z][a-z]{2} \d{4}) - (?P<end_date>\d{2} [A-Z][a-z]{2} \d{4})\n"
)


@pdfrenamer
def statement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("statement")
    first_page = document[1]

    # Cheap, specific identification first.
    if _ACCOUNT_DETAILS_IDENTIFIER not in first_page:
        return None

    logger.debug("Found likely Zopa Bank statement.")

    # From here on this is ours: assert rather than silently returning None.
    date_match = next(first_page.find_all_matching_regex(_DATE_RANGE_RE), None)
    assert date_match is not None, "date range not found"

    # Parse the dates
    end_date_str = date_match.group("end_date")
    end_date = datetime.strptime(end_date_str, "%d %b %Y")

    # Extract the account holder from the first box (name is on line 1)
    account_holder = first_page[0].strip()

    # Extract account number
    account_number_idx = first_page.index(_ACCOUNT_NUMBER_LABEL) + 1
    account_number = first_page[account_number_idx].strip()

    return NameComponents(
        end_date,
        _SERVICE,
        account_holder,
        STATEMENT,
        account_number=account_number,
    )
