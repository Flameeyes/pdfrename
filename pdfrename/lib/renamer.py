# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dataclasses
import datetime
import functools
import inspect
import logging
import re
import typing
from collections.abc import Callable, Iterator, Sequence

from . import pdf_document, utils


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
    additional_components: Sequence[str] = ()

    @property
    def account_holders(self) -> Sequence[str]:
        if isinstance(self.account_holder, str):
            return (self.account_holder,)
        else:
            return self.account_holder

    def render_filename(
        self, include_account_holder: bool, drop_honorific: bool
    ) -> str:
        filename_components = []

        filename_components.append(self.date.strftime("%Y-%m-%d"))

        filename_components.append(self.service_name)

        if include_account_holder and self.account_holder:
            account_holder = " & ".join(
                utils.normalize_account_holder_name(name, drop_honorific)
                for name in self.account_holders
            )

            filename_components.append(account_holder)

        filename_components.append(self.document_type)

        filename_components.extend(self.additional_components)

        filename = " - ".join(filename_components) + ".pdf"

        if re.search("[/:]", filename):
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
