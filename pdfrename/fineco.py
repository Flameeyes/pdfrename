# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from typing import Optional

import dateparser

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .lib import pdf_document


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

    account_holder_start = account_holder_str.index("Account Holders") + len("Account Holders")
    account_holder = account_holder_str[account_holder_start:].strip()

    return NameComponents(date, "FinecoBank", account_holder, "Statement")
