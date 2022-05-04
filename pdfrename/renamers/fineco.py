# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re
from typing import Optional

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def quarterly_statement(
    document: pdf_document.Document,
) -> Optional[NameComponents]:
    # We know the Fineco statements use LTFigure so they show up as a single,
    # long text string.
    if len(document[1]) != 1:
        return None

    (text,) = document[1]

    if not "FinecoBank S.p.A." in text and not "Bank Statement" in text:
        return None

    _, date_str, account_holder_str, _ = text.split("?", 3)

    # We don't know if the spacing is always preserved or dropped, so let's
    # play it relatively safe.
    date_start = date_str.index("Date") + 4
    date = dateparser.parse(date_str[date_start:])

    account_holder_start = account_holder_str.index("Account Holders") + len(
        "Account Holders"
    )
    account_holder = account_holder_str[account_holder_start:].strip()

    return NameComponents(date, "FinecoBank", account_holder, "Statement")


@pdfrenamer
def profit_loss(
    document: pdf_document.Document,
) -> Optional[NameComponents]:
    logger = _LOGGER.getChild("profit_loss")
    try:
        first_page = document[1]
    except IndexError:
        return None

    if not (first_page[0].startswith('P&L SUMMARY\n') and first_page[1].startswith('Dossier: ') and first_page[2].startswith("Dear\n")):
        return None
    
    account_holder = first_page[2].split('\n', 2)[1]

    date_match = re.search(r"realised P&L for transactions settled from \n([0-9]{2}/[0-9]{2}/[0-9]{4})\n", first_page[3])
    if not date_match:
        logger.debug("Failed to match date.")
        return None

    date = datetime.datetime.strptime(date_match.group(1), "%d/%m/%Y")

    return NameComponents(date, "FinecoBank", account_holder, "P&L Summary")
