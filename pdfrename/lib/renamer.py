# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterator, List, Optional, Sequence, Tuple, TypeVar

from . import pdf_document
from .. import components

Boxes = Sequence[str]
RenamerV1 = Callable[[Boxes, logging.Logger], Optional[components.NameComponents]]
RenamerV2 = Callable[[pdf_document.Document], Optional[components.NameComponents]]

Renamer = TypeVar("Renamer", RenamerV1, RenamerV2)

_ALL_RENAMERS: List[Tuple[Renamer, int]] = []


def pdfrenamer(func: Renamer) -> Renamer:

    version = 2 if len(inspect.signature(func).parameters) == 1 else 1

    _ALL_RENAMERS.append((func, version))

    return func


def try_all_renamers(
    document: pdf_document.Document, tool_logger: logging.Logger
) -> Iterator[components.NameComponents]:
    text_boxes = document[1]

    if not text_boxes:
        tool_logger.warning(f"No text boxes found on first page.")
        return None

    for renamer, version in _ALL_RENAMERS:
        try:
            if version == 1:
                name = renamer(text_boxes, tool_logger)
            else:
                name = renamer(document)

            if name:
                yield name
        except Exception:
            logging.exception(
                f"Renamer {renamer} failed on file {document.original_filename}"
            )
