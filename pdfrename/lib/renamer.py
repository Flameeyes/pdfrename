# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, Iterator, List, Sequence, Optional

from . import pdf_document
from .. import components

Boxes = Sequence[str]
Renamer = Callable[[Boxes, logging.Logger], Optional[components.NameComponents]]

_ALL_RENAMERS: List[Renamer] = []


def pdfrenamer(func: Renamer) -> Renamer:
    _ALL_RENAMERS.append(func)

    return func


def try_all_renamers(
    document: pdf_document.Document, tool_logger: logging.Logger
) -> Iterator[components.NameComponents]:
    text_boxes = document[1]

    if not text_boxes:
        tool_logger.warning(f"No text boxes found on first page.")
        return None

    for renamer in _ALL_RENAMERS:
        try:
            if name := renamer(text_boxes, tool_logger):
                yield name
        except Exception:
            logging.exception(
                f"Renamer {renamer} failed on file {document.original_filename}"
            )
