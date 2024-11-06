# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

from more_itertools import first, one

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)


def _statement_generic(
    document: pdf_document.Document,
    localised_website: str,
    localised_account_holder_string: str,
    localised_page_string: str,
    localised_membership_string: str,
    localised_date_string: str,
) -> NameComponents | None:
    logger = _LOGGER.getChild("statement_generic")

    text_boxes = document[1]  # Only need the first page.

    if len(text_boxes) < 4:
        return None

    if not any(
        text_boxes.find_all_matching_regex(
            re.compile(rf"^(?:www\.)?{localised_website}\n")
        )
    ):
        return None

    logger.debug("Found possible American Express document")

    account_holder_box = text_boxes.find_box_starting_with(
        f"{localised_account_holder_string}\n"
    )
    logger.debug("Account holder: %r", account_holder_box)
    assert account_holder_box
    _, account_holder_name, _ = account_holder_box.split("\n")

    account_holder_index = text_boxes.index(account_holder_box)

    membership_match = re.match(
        rf"^{localised_membership_string}\n[x0-9]{{4}}-[x0-9]{{6}}-([0-9]{{5}})\n$",
        text_boxes[account_holder_index + 1],
    )

    if not membership_match:
        logger.debug("No membership number information matched.")
        return None

    date_box = text_boxes[account_holder_index + 2]
    assert date_box.startswith(f"{localised_date_string}\n")
    _, date_str, _ = date_box.split("\n")

    statement_date = datetime.datetime.strptime(date_str, "%d/%m/%y")

    # Document type is usually before the "Page" box. Note that this is
    # not always "Page X of Y", depending on the age of the statement.
    page_mention_index = first(
        text_boxes.find_all_indexes_matching_regex(
            re.compile(f"^{localised_page_string} .+")
        )
    )

    # If the page mention is further in the page, it's likely an old template instead.
    # In that case, or if we can't find one, assume it's just before the account holder name.
    if not page_mention_index or page_mention_index > 5:
        document_type_box = text_boxes[account_holder_index - 1]
    else:
        document_type_box = text_boxes[page_mention_index - 1]

    document_type_lines = document_type_box.strip().split("\n")
    if len(document_type_lines) == 1:
        document_type = one(document_type_lines)
    else:
        document_type = document_type_lines[1]

    return NameComponents(
        statement_date,
        "American Express",
        account_holder_name.strip(),
        document_type,
        account_number=f"xx-{membership_match.group(1)}",
    )


@pdfrenamer
def statement_gbr(document: pdf_document.Document) -> NameComponents | None:
    components = _statement_generic(
        document,
        "americanexpress.co.uk",
        "Prepared for",
        "Page",
        "Membership Number",
        "Date",
    )

    if components and components.document_type == "Statement of Account":
        components.document_type = "Statement"

    return components


@pdfrenamer
def statement_ita(document: pdf_document.Document) -> NameComponents | None:
    # This was only tested on 2011 statements (!)
    return _statement_generic(
        document,
        "americanexpress.it",
        "Gentile Titolare",
        "Pagina",
        "Numero di Carta",
        "Data",
    )
