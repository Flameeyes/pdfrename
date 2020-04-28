# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re

from typing import Optional

from components import NameComponents


def _extract_account_holder_name(address: str) -> str:
    return address.split("\n")[0].strip().title()


def _parse_date(date: str) -> datetime.datetime:
    """Parse Santander documents date into a datetime object.

    Santander appears to use a fairly verbose date format, including the ordinal suffixes
    (1st, 2nd, 3rd, 4th). Sometimes with a full month name (September) and other times
    with a short month name (Apr).

    To make sure to support both, always match the first three letters of the month, since
    English month names and their abbreviations match.
    """
    parsed_date = re.match(
        "^([0-9]{1,2})[a-z]{2} ([A-Z][a-z]{2})[a-z]* ([0-9]{4})$", date
    )
    assert parsed_date

    return datetime.datetime.strptime(" ".join(parsed_date.groups()), "%d %b %Y")


def try_santander(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("santander")

    is_santander_credit_card = any(
        box == "Santander Credit Card \n" for box in text_boxes
    )

    if is_santander_credit_card:
        # Always include the account holder name, which is found in the second text box.
        account_holder_name = _extract_account_holder_name(text_boxes[1])

        # Could be an annual statement, look for it.
        is_annual_statement = any(
            box.startswith("Annual Statement:") for box in text_boxes
        )

        if is_annual_statement:
            document_type = "Annual Statement"

            period_line = [
                box for box in text_boxes if box.startswith("Annual Statement:")
            ]
            assert len(period_line) == 1

            logger.debug("found period specification: %r", period_line[0])

            period_match = re.match(
                r"^Annual Statement: [0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4} to ([0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4})\n",
                period_line[0],
            )
            assert period_match
            statement_date = _parse_date(period_match.group(1))
        else:
            document_type = "Statement"

            period_line = [
                box for box in text_boxes if box.startswith("Account summary as at:")
            ]
            assert len(period_line) == 1

            logger.debug("found period specification: %r", period_line[0])

            period_match = re.match(
                r"^Account summary as at: ([0-9]{1,2}[a-z]{2} [A-Z][a-z]+ [0-9]{4}) for card number ending [0-9]{4}\n$",
                period_line[0],
            )
            assert period_match
            statement_date = _parse_date(period_match.group(1))

        return NameComponents(
            statement_date,
            "Santander",
            account_holder=account_holder_name,
            additional_components=("Credit Card", document_type),
        )

    is_santander_select = any(box == "Select Current Account\n" for box in text_boxes)

    if is_santander_select:
        # Always include the account holder name, which is found in the second text box.
        account_holder_name = _extract_account_holder_name(text_boxes[2])

        period_line = [
            box for box in text_boxes if box.startswith("Your account summary for  \n")
        ]
        assert len(period_line) == 1

        logger.debug("found period specification: %r", period_line[0])

        period_match = re.match(
            r"^Your account summary for  \n[0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4} to ([0-9]{1,2}[a-z]{2} [A-Z][a-z]{2} [0-9]{4})\n$",
            period_line[0],
        )
        assert period_match
        statement_date = _parse_date(period_match.group(1))

        return NameComponents(
            statement_date,
            "Santander",
            account_holder=account_holder_name,
            additional_components=("Select Current Account", "Statement"),
        )
