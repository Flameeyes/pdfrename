# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from collections.abc import Callable, Iterator, Sequence
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any, BinaryIO, Final

import pdfminer.high_level
import pdfminer.layout
import pdfminer.pdfdocument
import pdfminer.pdfparser
from more_itertools import only

_LOGGER = logging.getLogger(__name__)

_AUTHOR_METADATA = "Author"
_CREATOR_METADATA = "Creator"
_PRODUCER_METADATA = "Producer"
_SUBJECT_METADATA = "Subject"
_TITLE_METADATA = "Title"
_CREATION_DATE_METADATA = "CreationDate"


class PageTextBoxes:
    _boxes: Final[Sequence[str]]

    def __init__(self, text_boxes: Sequence[str]) -> None:
        self._boxes = text_boxes

    def __len__(self) -> int:
        return len(self._boxes)

    def __getitem__(self, key: Any) -> str:
        return self._boxes[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._boxes)

    def __contains__(self, item: Any) -> bool:
        return item in self._boxes

    def index(self, content: str) -> int:
        return self._boxes.index(content)

    def find_box_with_match(self, match: Callable[[str], bool]) -> str | None:
        return only(box for box in self._boxes if match(box))

    def find_index_with_match(self, match: Callable[[str], bool]) -> int | None:
        if box := self.find_box_with_match(match):
            return self.index(box)

        return None

    def find_all_indexes_matching_regex(
        self, pattern: re.Pattern[str]
    ) -> Iterator[int]:
        for idx, box in enumerate(self._boxes):
            if pattern.match(box):
                yield idx

    def find_all_matching_regex(
        self, pattern: re.Pattern[str]
    ) -> Iterator[re.Match[str]]:
        for box in self._boxes:
            if match := pattern.match(box):
                yield match

    def find_box_starting_with(self, prefix: str) -> str | None:
        return self.find_box_with_match(lambda box: box.startswith(prefix))

    def find_index_starting_with(self, prefix: str) -> int | None:
        return self.find_index_with_match(lambda box: box.startswith(prefix))


class Document:
    original_filename: Final[Path]
    _pdf_file: Final[BinaryIO]
    doc: Final[pdfminer.pdfdocument.PDFDocument]
    _logger: Final[logging.Logger]
    _extracted_pages: Final[dict[int, PageTextBoxes]]

    def __init__(
        self,
        filename: Path,
        *,
        pdf_file: BinaryIO | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.original_filename = filename
        if pdf_file is None:
            pdf_file = self.original_filename.open("rb")
        self._pdf_file = pdf_file

        self._logger = logger or _LOGGER

        try:
            pdfminer.high_level.extract_pages(self._pdf_file)  # type: ignore
        except pdfminer.pdfparser.PDFSyntaxError as error:
            raise ValueError(f"Invalid PDF file {self.original_filename}: {error}")

        self._parser = pdfminer.pdfparser.PDFParser(self._pdf_file)
        self.doc = pdfminer.pdfdocument.PDFDocument(self._parser)

        self._extracted_pages = {}

        # Always extract the first page.
        self.get_textboxes(1)

    def close(self) -> None:
        self._parser.close()

    def get_textboxes(self, page: int) -> PageTextBoxes:
        if page < 1:
            raise IndexError("Document pages are 1-indexed.")

        if page not in self._extracted_pages:
            self._logger.debug(
                f"{self.original_filename}: page {page} is beyond the extracted pages, extracting now."
            )

            extract_pages_generator = pdfminer.high_level.extract_pages(
                self._pdf_file, page_numbers=(page - 1,)  # type: ignore
            )

            try:
                page_content = list(next(extract_pages_generator))
            except StopIteration as e:
                raise IndexError(
                    f"{self.original_filename} does not have page {page}"
                ) from e

            if len(page_content) == 1 and isinstance(
                page_content[0], pdfminer.layout.LTFigure
            ):
                self._logger.debug(
                    f"{self.original_filename} p{page}: figure-based PDF, extracting raw text instead."
                )
                page_text = pdfminer.high_level.extract_text(
                    self._pdf_file, page_numbers=(page - 1,)  # type: ignore
                )
                text_boxes = [page_text]
            else:
                text_boxes = [
                    obj.get_text()
                    for obj in page_content
                    if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal)
                ]

            if not text_boxes:
                self._logger.debug(
                    f"{self.original_filename} p{page}: no text boxes found: {page_content!r}"
                )
            else:
                self._logger.debug(f"{self.original_filename} p{page}: {text_boxes!r}")

            self._extracted_pages[page] = PageTextBoxes(text_boxes)

        return self._extracted_pages[page]

    def __getitem__(self, key: Any) -> PageTextBoxes:
        if not isinstance(key, int):
            raise TypeError("Only integer page indexes are supported.")
        return self.get_textboxes(key)

    def _document_metadata(self, metadata_name: str) -> bytes | None:
        self._logger.debug(
            f"{self.original_filename}: extracted info {self.doc.info!r}"
        )

        for info in self.doc.info:
            if metadata_name in info:
                return info[metadata_name]

        return None

    _DATE_PROPERTY_RE: Final[re.Pattern[bytes]] = re.compile(
        rb"^D:(\d{14})(?:Z|([+-]\d{2})'(\d{2})')?$"
    )

    @classmethod
    def _date_property_to_datetime(cls, date_property: bytes) -> datetime | None:
        if not (date_match := cls._DATE_PROPERTY_RE.fullmatch(date_property)):
            return None

        date_format = "%Y%m%d%H%M%S"
        date_str = date_match.group(1).decode("ascii")
        if date_match.group(2) is not None:
            # There's timezone information, extract it and concatenate it.
            tz = date_match.group(2) + date_match.group(3)
            date_str += tz.decode("ascii")
            date_format += "%z"

        return datetime.strptime(date_str, date_format)

    @cached_property
    def author(self) -> bytes | None:
        return self._document_metadata(_AUTHOR_METADATA)

    @cached_property
    def creator(self) -> bytes | None:
        return self._document_metadata(_CREATOR_METADATA)

    @cached_property
    def producer(self) -> bytes | None:
        return self._document_metadata(_PRODUCER_METADATA)

    @cached_property
    def subject(self) -> bytes | None:
        return self._document_metadata(_SUBJECT_METADATA)

    @cached_property
    def title(self) -> bytes | None:
        return self._document_metadata(_TITLE_METADATA)

    @cached_property
    def creation_date(self) -> datetime | None:
        if creation_date := self._document_metadata(_CREATION_DATE_METADATA):
            return self._date_property_to_datetime(creation_date)

        return None
