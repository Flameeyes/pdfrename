# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Iterator, List, Sequence

import pdfminer.high_level
import pdfminer.layout
import pdfminer.pdfdocument
import pdfminer.pdfparser

_LOGGER = logging.getLogger(__name__)

_AUTHOR_METADATA = "Author"
_CREATOR_METADATA = "Creator"
_PRODUCER_METADATA = "Producer"
_SUBJECT_METADATA = "Subject"
_TITLE_METADATA = "Title"


class PageTextBoxes:
    _boxes: Sequence[str]

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
        found_boxes = [box for box in self._boxes if match(box)]
        if not found_boxes:
            return None
        assert len(found_boxes) == 1
        return found_boxes[0]

    def find_index_with_match(self, match: Callable[[str], bool]) -> int | None:
        if box := self.find_box_with_match(match):
            return self.index(box)

        return None

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
    original_filename: str
    doc: pdfminer.pdfdocument.PDFDocument
    _extracted_pages: List[PageTextBoxes]

    def __init__(self, filename: str) -> None:
        self.original_filename = filename

        try:
            self._extract_pages_generator = pdfminer.high_level.extract_pages(filename)
        except pdfminer.pdfparser.PDFSyntaxError as error:
            raise ValueError(f"Invalid PDF file {filename}: {error}")

        with open(self.original_filename, "rb") as pdf_file:
            parser = pdfminer.pdfparser.PDFParser(pdf_file)
            self.doc = pdfminer.pdfdocument.PDFDocument(parser)

        self._extracted_pages = []

    def get_textboxes(self, page: int) -> PageTextBoxes:
        if page < 1:
            raise IndexError("Document pages are 1-indexed.")

        if page > len(self._extracted_pages):
            _LOGGER.debug(
                f"{self.original_filename}: page {page} is beyond the extracted pages, extracting now."
            )
            for new_page_idx in range(len(self._extracted_pages) + 1, page + 1):
                try:
                    page_content = list(next(self._extract_pages_generator))
                except StopIteration:
                    raise IndexError(
                        f"{self.original_filename} does not have page {new_page_idx}"
                    )

                if len(page_content) == 1 and isinstance(
                    page_content[0], pdfminer.layout.LTFigure
                ):
                    _LOGGER.debug(
                        f"{self.original_filename} p{new_page_idx}: figure-based PDF, extracting raw text instead."
                    )
                    page_text = pdfminer.high_level.extract_text(
                        self.original_filename, page_numbers=[new_page_idx - 1]
                    )
                    text_boxes = [page_text]
                else:
                    text_boxes = [
                        obj.get_text()
                        for obj in page_content
                        if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal)
                    ]

                if not text_boxes:
                    _LOGGER.debug(
                        f"{self.original_filename} p{new_page_idx}: no text boxes found: {page_content!r}"
                    )
                else:
                    _LOGGER.debug(
                        f"{self.original_filename} p{new_page_idx}: {text_boxes!r}"
                    )

                self._extracted_pages.append(PageTextBoxes(text_boxes))

        return self._extracted_pages[page - 1]

    def __getitem__(self, key: Any) -> PageTextBoxes:
        if not isinstance(key, int):
            raise TypeError("Only integer page indexes are supported.")
        return self.get_textboxes(key)

    def _document_metadata(self, metadata_name: str) -> bytes | None:
        _LOGGER.debug(f"{self.original_filename}: extracted info {self.doc.info!r}")

        for info in self.doc.info:
            if metadata_name in info:
                return info[metadata_name]

        return None

    @property
    def author(self) -> bytes | None:
        return self._document_metadata(_AUTHOR_METADATA)

    @property
    def creator(self) -> bytes | None:
        return self._document_metadata(_CREATOR_METADATA)

    @property
    def producer(self) -> bytes | None:
        return self._document_metadata(_PRODUCER_METADATA)

    @property
    def subject(self) -> bytes | None:
        return self._document_metadata(_SUBJECT_METADATA)

    @property
    def title(self) -> bytes | None:
        return self._document_metadata(_TITLE_METADATA)
