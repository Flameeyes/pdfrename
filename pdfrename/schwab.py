# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re
from typing import Optional, Sequence

import dateparser

from .lib.renamer import NameComponents, pdfrenamer
from .lib.utils import extract_account_holder_from_address, find_box_starting_with


def _find_statement_date(text_boxes: Sequence[str], logger) -> datetime.datetime:
    # The actual date of the statement would be in the third page, but since we only
    # converted the first page, we wing it a bit.
    period_box = find_box_starting_with(text_boxes, "Statement Period\n")
    if not period_box:
        # older statements
        period_box = find_box_starting_with(text_boxes, "Statement Period: ")

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

    return dateparser.parse(period_end_str, languages=["en"])


@pdfrenamer
def letter(text_boxes: Sequence[str], parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("schwab.letter")

    # Older brokerage accounts (2016)
    if text_boxes[0].startswith("Schwab One® International Account\n"):
        logger.debug("Schwab One brokerage account statement (2016).")
        address_index = text_boxes.index("Mail To\n") + 1
        address_box = text_boxes[address_index]

        account_holder = extract_account_holder_from_address(address_box)
        assert account_holder

        statement_date = _find_statement_date(text_boxes, logger)

        return NameComponents(
            statement_date, "Schwab", account_holder, "Brokerage Statement"
        )

    # Brokerage Accounts, Trade Confirmations and Year-End documents from 2017 onwards.
    if text_boxes[0].startswith("Schwab One® International Account"):

        account_holder = text_boxes[0].split("\n")[1].strip().title()
        assert account_holder

        if text_boxes[2] == "Trade Confirmation\n":
            logger.debug("Schwab One Trade Confirmation")
            logger.warning(
                "Cannot rename this document, as date is not present on the first page!"
            )
            return None

        # Look for different types of year end documents.
        year_end_gain_losses = [
            box for box in text_boxes if "Year-End Schwab Gain/Loss Report" in box
        ]
        year_end_summary = [box for box in text_boxes if "YEAR-END SUMMARY" in box]

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
            date_box = find_box_starting_with(text_boxes, "Date Prepared: ")
            assert date_box
            date_match = re.search(
                r"^Date Prepared:  ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})\n$", date_box
            )
            assert date_match

            document_date = dateparser.parse(date_match.group(1), languages=["en"])
            document_type = "Year End Summary"
        else:
            logger.debug("Schwab One brokerage account statement.")
            document_date = _find_statement_date(text_boxes, logger)
            document_type = "Brokerage Statement"

        return NameComponents(document_date, "Schwab", account_holder, document_type)

    # Letters
    if any(
        "Charles Schwab & Co., Inc. All rights reserved." in box for box in text_boxes
    ):
        logger.debug("Letter, possibly.")

        # Newer (2018) letters.
        if "Dear Client,\n" in text_boxes:
            date_str = text_boxes[0].split("\n")[0]
            logger.debug("Found date: %r", date_str)

            letter_date = dateparser.parse(date_str, languages=["en"])

            # The address is two boxes before the "Dear Client,".
            address_index = text_boxes.index("Dear Client,\n") - 3

            account_holder = extract_account_holder_from_address(
                text_boxes[address_index]
            )
        else:
            account_holder = extract_account_holder_from_address(text_boxes[0])
            letter_date = dateparser.parse(text_boxes[1], languages=["en"])

        assert account_holder

        return NameComponents(letter_date, "Schwab", account_holder, "Letter")
