# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
from typing import Any, List, Sequence

import pdfminer.high_level
import pdfminer.layout

_LOGGER = logging.getLogger(__name__)


class Document:

    original_filename: str
    _extracted_pages: List[Sequence[str]]

    def __init__(self, filename: str) -> None:
        self.original_filename = filename

        try:
            self._extract_pages_generator = pdfminer.high_level.extract_pages(filename)
        except pdfminer.pdfparser.PDFSyntaxError as error:
            raise ValueError(f"Invalid PDF file {filename}: {error}")

        self._extracted_pages = []

    def get_textboxes(self, page: int) -> Sequence[str]:
        if page < 1:
            raise IndexError("Document pages are 1-indexed.")

        if page > len(self._extracted_pages):
            _LOGGER.debug(
                f"{self.original_filename}: page {page} is beyond the extracted pages, extracting now."
            )
            for new_page_idx in range(len(self._extracted_pages) + 1, page + 1):
                try:
                    page_content = next(self._extract_pages_generator)
                except StopIteration:
                    raise IndexError(
                        f"{self.original_filename} does not have page {new_page_idx}"
                    )
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
                    self._extracted_pages.append(text_boxes)

        return self._extracted_pages[page - 1]

    def __getitem__(self, key: Any) -> Sequence[str]:
        if not isinstance(key, int):
            raise TypeError(f"Only integer page indexes are supported.")
        return self.get_textboxes(key)
