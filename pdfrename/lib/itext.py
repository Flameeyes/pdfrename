# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT
"""
Utilities to parse iText metadata.

A lot of PDFs are generated through iText libraries, which means it is possible
to guess some of the metadata of the document based on it.
"""

import re
from datetime import datetime
from typing import Final

from .pdf_document import Document

_ITEXT_CREATION_DATE: Final[str] = "CreationDate"


def did_itext_generate(document: Document) -> bool:
    return document.producer.startswith(b"iText ")


def _itext_date_to_datetime(itext_date: str) -> datetime:
    # We cannot _quite_ parse this correctly with strptime because the final offset is
    # not compatible, so translate it instead.
    date_match = re.match(r"^D:(\d{14})\+(\d{2})'(\d{2})'$", itext_date)
    if not date_match:
        raise ValueError(f"{itext_date!r} is not a valid iText date.")

    date_str = f"{date_match.group(1)}+{date_match.group(2)}{date_match.group(3)}"

    return datetime.strptime(date_str, "%Y%m%d%H%M%S%z")


def creation_date(document: Document) -> datetime | None:
    if not did_itext_generate(document):
        return

    creation_date = document._document_metadata(_ITEXT_CREATION_DATE).decode("ascii")

    return _itext_date_to_datetime(creation_date)
