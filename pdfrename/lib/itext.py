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
    producer = document.producer
    return producer.startswith(b"iText ") or producer.startswith(b"iText\xae 5")


def _itext_date_to_datetime(itext_date: str) -> datetime:
    # We cannot _quite_ parse this correctly with strptime because the final offset is
    # not compatible. Plus different versions appear to generate a slightly different
    # mangling of the timezone.
    date_match = re.match(r"^D:(\d{14})(Z|\+(\d{2})'(\d{2})')$", itext_date)
    if not date_match:
        raise ValueError(f"{itext_date!r} is not a valid iText date.")

    date_format = "%Y%m%d%H%M%S"
    if date_match.group(2) == "Z":
        date_str = date_match.group(1)
    else:
        date_str = f"{date_match.group(1)}+{date_match.group(3)}{date_match.group(4)}"
        date_format += "%z"

    return datetime.strptime(date_str, date_format)


def creation_date(document: Document) -> datetime | None:
    if not did_itext_generate(document):
        return

    creation_date = document._document_metadata(_ITEXT_CREATION_DATE).decode("ascii")

    return _itext_date_to_datetime(creation_date)
