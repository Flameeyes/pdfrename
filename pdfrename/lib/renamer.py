# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dataclasses
import datetime
import functools
import inspect
import logging
import typing
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from . import pdf_document, utils

# This is only implemented for Windows, unfortunately.
# So fall back to something else if not implemented.
try:

    from os.path import isreserved  # type: ignore[attr-defined]
except ImportError:

    def isreserved(path: Path) -> bool:
        path_s = str(path)
        return any(reserved_character in path_s for reserved_character in ":/\\")


class InvalidFilenameError(ValueError):
    """Raised when the generated filename is invalid.

    Only really used to report that the filename includes characters that are
    not valid in a filename (mostly, for Windows compatibility.)
    """


@dataclasses.dataclass
class NameComponents:
    date: datetime.datetime
    service_name: str
    account_holder: str | Sequence[str]
    document_type: str
    account_number: str | None = None
    document_number: str | None = None

    @property
    def account_holders(self) -> Sequence[str]:
        if isinstance(self.account_holder, str):
            return (self.account_holder,)
        else:
            return self.account_holder

    @property
    def normalized_account_holders(self) -> str | None:
        if not self.account_holder:
            return None

        return " & ".join(
            utils.normalize_account_holder_name(name, True)
            for name in self.account_holders
        )

    @property
    def normalized_document_number(self) -> str | None:
        """Normalize the document number in a form compatible with file names."""

        if not self.document_number:
            return None

        return self.document_number.replace("/", "-")

    def render_filename(self) -> Path:
        filename_components = []

        filename_components.append(self.date.strftime("%Y-%m-%d"))

        filename_components.append(self.service_name)

        if account_holders := self.normalized_account_holders:
            filename_components.append(account_holders)

        filename_components.append(self.document_type)

        if self.account_number:
            filename_components.append(self.account_number)

        if document_number := self.normalized_document_number:
            filename_components.append(document_number)

        filename = Path(" - ".join(filename_components) + ".pdf")

        if isreserved(filename) or len(filename.parts) > 1:
            raise InvalidFilenameError(f"Invalid filename '{filename}'")

        return filename


Boxes = Sequence[str]
RenamerV1 = Callable[[Boxes, logging.Logger], NameComponents | None]
RenamerV2 = Callable[[pdf_document.Document], NameComponents | None]

AnyRenamer = RenamerV1 | RenamerV2

_ALL_RENAMERS: list[RenamerV2] = []


def _convert_to_renamer_v2(renamer: RenamerV1) -> RenamerV2:
    @functools.wraps(renamer)
    def _wrapper(document: pdf_document.Document) -> NameComponents | None:
        first_page_text_boxes = list(document[1])
        if not first_page_text_boxes:
            return None

        new_logger = logging.getLogger(renamer.__module__)
        return renamer(first_page_text_boxes, new_logger)

    return _wrapper


def pdfrenamer(func: AnyRenamer) -> RenamerV2:
    version = 2 if len(inspect.signature(func).parameters) == 1 else 1

    match version:
        case 2:
            func = typing.cast(RenamerV2, func)
        case 1:
            func = _convert_to_renamer_v2(typing.cast(RenamerV1, func))

    func = typing.cast(RenamerV2, func)

    _ALL_RENAMERS.append(func)

    return func


def try_all_renamers(document: pdf_document.Document) -> Iterator[NameComponents]:
    for renamer in _ALL_RENAMERS:
        try:
            if name := renamer(document):
                yield name
        except Exception:
            logging.exception(f"{document.original_filename}: renamer {renamer} failed")
