# SPDX-FileCopyrightText: 2024 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT
"""
Utilities to parse iText metadata.

A lot of PDFs are generated through iText libraries, which means it is possible
to guess some of the metadata of the document based on it.
"""

from .pdf_document import Document


def did_itext_generate(document: Document) -> bool:
    if not (producer := document.producer):
        return False
    return producer.startswith(b"iText ") or producer.startswith(b"iText\xae 5")
