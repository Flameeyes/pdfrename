# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import dateparser
import re

from typing import Optional, Sequence

from components import NameComponents
from utils import extract_account_holder_from_address, find_box_starting_with


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


def try_schwab(text_boxes: Sequence[str], parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("schwab")

    # Brokerage Accounts from 2017 onwards.
    if text_boxes[0].startswith("Schwab One® International Account   of\n"):
        logger.debug("Schwab One brokerage account statement.")

        account_holder = text_boxes[0].split("\n")[1].strip().title()
        assert account_holder

        statement_date = _find_statement_date(text_boxes, logger)

        return NameComponents(
            statement_date, "Schwab", account_holder, "Brokerage Statement"
        )

    # Older brokerage accounts (2016)
    if text_boxes[0].startswith("Schwab One® International Account\n"):
        address_index = text_boxes.index("Mail To\n") + 1
        address_box = text_boxes[address_index]

        account_holder = extract_account_holder_from_address(address_box)
        assert account_holder

        statement_date = _find_statement_date(text_boxes, logger)

        return NameComponents(
            statement_date, "Schwab", account_holder, "Brokerage Statement"
        )
