# SPDX-FileCopyrightText: 2023 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def estatement(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("estatement")

    if document.author != b"Fiserv" or document.creator != b"eStatements":
        return None

    logger.debug("Metadata suggest Fiserv eStatement")

    # Good news, Fiserv follows the same template for years and there are
    # some very obvious fixed positions.
    # Bad news, they don't explicitly put the name of the issuer anywhere
    # but the giro credit tab at the bottom of the first page.

    first_page = document[1]
    credit_limit_index = first_page.index("Total Credit Limit\n")

    if credit_limit_index is None:
        logger.debug("But could not find the Summary table.")
        return None

    # Annoyingly this is not at a fix offset! Once we find the beginning
    # of the summary table we attempt the next ~8 boxes until one is a
    # simple date.
    for date_index in range(credit_limit_index + 1, credit_limit_index + 8):
        statement_date = dateparser.parse(first_page[date_index], languages=["en"])
        if statement_date is not None:
            break
    else:
        logging.debug("Unable to find a valid statement date")
        return None

    account_holder = extract_account_holder_from_address(first_page[0])

    # This is a horrible hack but it appears to be stable enough!
    minimum_payment_box_index = first_page.find_index_with_match(
        lambda box: "Please refer overleaf for further details.\n" in box
    )
    if minimum_payment_box_index is None:
        return None

    possible_address_boxes = [
        box
        for box in first_page[minimum_payment_box_index:]
        # We want a box that has more than two lines (there's at least three in most
        # addresses), but where newlines are not literally half of the content, as
        # those are usually vertical boxes or barcodes instead.
        if box.count("\n") > 2 and box.count("\n") < len(box) / 2
    ]

    if len(possible_address_boxes) != 1:
        logger.debug("Unable to identify the correct card issuer!")
        return None

    bank_name = possible_address_boxes[0].split("\n", 1)[0]

    # To make it easier to detect different cards, go and find the second page, where
    # the card number would be. If it can't be found just ignore it though.
    additional_components = []

    second_page = document[2]
    if second_page[0].startswith("2 of ") and second_page[1] == "Cardholder\n":
        card_match = re.match(
            r"[0-9]{4} [0-9]{4} [0-9]{4} ([0-9]{4})\n", second_page[4]
        )

        if card_match:
            additional_components += [f"xx-{card_match.group(1)}"]

    return NameComponents(
        statement_date,
        bank_name,
        account_holder,
        "Credit Card Statement",
        additional_components=additional_components,
    )
