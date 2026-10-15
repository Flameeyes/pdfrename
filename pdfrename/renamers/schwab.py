# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

import dateparser

from ..doctypes.en import STATEMENT
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


def _find_statement_date(
    first_page: pdf_document.PageTextBoxes, logger
) -> datetime.datetime:
    # The actual date of the statement would be in the third page, but since we only
    # converted the first page, we wing it a bit.
    period_box = first_page.find_box_starting_with("Statement Period\n")
    if not period_box:
        # older statements
        period_box = first_page.find_box_starting_with("Statement Period: ")

    logger.debug("found period specification: %r", period_box)
    assert period_box

    # This matches when the period is strictly within a month.
    period_match = re.search(
        r"Statement Period(?:\n|: )([A-Z][a-z]+ )[0-9]{1,2}-([0-9]{1,2}, [0-9]{4})\n",
        period_box,
    )
    if period_match:
        period_end_str = period_match.group(1) + period_match.group(2)
    else:
        period_match = re.search(
            r"Statement Period(?:\n|: )[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4} to[\n ]([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})\n",
            period_box,
        )
        assert period_match
        period_end_str = period_match.group(1)

    date = dateparser.parse(period_end_str, languages=["en"])
    assert date is not None
    return date


@pdfrenamer
def letter(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if not first_page:
        return None

    logger = _LOGGER.getChild("schwab.letter")

    # Older brokerage accounts (2016)
    if first_page[0].startswith("Schwab One® International Account\n"):
        logger.debug("Schwab One brokerage account statement (2016).")
        address_index = first_page.index("Mail To\n") + 1
        address_box = first_page[address_index]

        account_holder = extract_account_holder_from_address(address_box)
        assert account_holder

        statement_date = _find_statement_date(first_page, logger)

        return NameComponents(
            statement_date, "Charles Schwab", account_holder, "Brokerage Statement"
        )

    # Brokerage Accounts, Trade Confirmations and Year-End documents from 2017 onwards.
    if first_page[0].startswith("Schwab One® International Account"):
        account_holder = first_page[0].split("\n")[1].strip().title()
        assert account_holder

        if first_page[2] == "Trade Confirmation\n":
            logger.debug("Schwab One Trade Confirmation")
            logger.warning(
                "Cannot rename this document, as date is not present on the first page!"
            )
            return None

        # Look for different types of year end documents.
        year_end_gain_losses = [
            box for box in first_page if "Year-End Schwab Gain/Loss Report" in box
        ]
        year_end_summary = [box for box in first_page if "YEAR-END SUMMARY" in box]

        if year_end_gain_losses:
            logger.debug("Year End Gain/Loss Report")
            date_match = re.search(
                r"\nPrepared on ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})\n",
                year_end_gain_losses[0],
            )
            assert date_match  # Else we don't have the right document.
            document_date = dateparser.parse(date_match.group(1), languages=["en"])
            document_type = "Year End Gain-Losses Report"
        elif year_end_summary:
            logger.debug("Year End Summary")
            date_box = first_page.find_box_starting_with("Date Prepared: ")
            assert date_box
            date_match = re.search(
                r"^Date Prepared:  ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})\n$",
                date_box,
            )
            assert date_match

            document_date = dateparser.parse(date_match.group(1), languages=["en"])
            document_type = "Year End Summary"
        else:
            logger.debug("Schwab One brokerage account statement.")
            document_date = _find_statement_date(first_page, logger)
            document_type = "Brokerage Statement"

        assert document_date is not None
        return NameComponents(
            document_date, "Charles Schwab", account_holder, document_type
        )

    # Letters
    if any(
        "Charles Schwab & Co., Inc. All rights reserved." in box for box in first_page
    ):
        logger.debug("Letter, possibly.")

        # Newer (2018) letters.
        if "Dear Client,\n" in first_page:
            date_str = first_page[0].split("\n")[0]
            logger.debug("Found date: %r", date_str)

            letter_date = dateparser.parse(date_str, languages=["en"])

            # The address is two boxes before the "Dear Client,".
            address_index = first_page.index("Dear Client,\n") - 3

            account_holder = extract_account_holder_from_address(
                first_page[address_index]
            )
        else:
            account_holder = extract_account_holder_from_address(first_page[0])
            letter_date = dateparser.parse(first_page[1], languages=["en"])

        assert account_holder
        assert letter_date is not None

        return NameComponents(letter_date, "Charles Schwab", account_holder, "Letter")

    return None


@pdfrenamer
def account_summary(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if not first_page:
        return None

    logger = _LOGGER.getChild("schwab.account_summary")

    # Identify account summary documents
    if not first_page[0].startswith("Schwab One International® Account of\n"):
        return None

    logger.debug("Found Schwab One Account Summary")

    # Extract account holder
    account_holder = first_page[1].strip()
    assert account_holder

    # Find statement date by looking directly for the date pattern in the PDF
    # Looking at the structure from our debugging:
    # Box 3: 'Statement Period\n'
    # Box 4: '<account-number>\n' (account number)
    # Box 5: '<date-range>\n' (date)
    period_idx = first_page.index("Statement Period\n")
    # The date should be right after the account number, which is immediately after "Statement Period"
    # In our PDF, this is box 5
    assert period_idx + 2 < len(first_page), "not enough boxes for date"
    date_box = first_page[period_idx + 2]
    period_end_str = date_box.strip()
    logger.debug("Using date from position %d: %r", period_idx + 2, period_end_str)

    # Parse date range and extract end date (statements are issued at end of period)
    # Format is like "July 1-31, 2026"
    date_match = re.search(
        r"([A-Z][a-z]+) (\d{1,2})-(\d{1,2}), (\d{4})", period_end_str
    )
    if date_match:
        month_name = date_match.group(1)
        end_day = date_match.group(3)
        year = date_match.group(4)
        # Reconstruct as end date
        end_date_str = f"{month_name} {end_day}, {year}"
        logger.debug("Extracted end date string: %r", end_date_str)
        statement_date = dateparser.parse(end_date_str, languages=["en"])
    else:
        # Fall back to regular parsing
        statement_date = dateparser.parse(period_end_str, languages=["en"])
    assert statement_date is not None, f"Could not parse date from {period_end_str}"

    # Account number is the box after "Account Number"
    account_number = None
    account_number_label_box = first_page.find_box_starting_with("Account Number\n")
    if account_number_label_box is not None:
        account_number_idx = first_page.index(account_number_label_box) + 2
        if account_number_idx < len(first_page):
            account_number = first_page[account_number_idx].strip()
            # Keep the original XXXX-YYYY format, including ****- masking

    return NameComponents(
        statement_date,
        "Charles Schwab",
        account_holder,
        STATEMENT,
        account_number=account_number,
    )
