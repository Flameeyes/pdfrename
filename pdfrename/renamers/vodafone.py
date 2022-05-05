# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
# SPDX-FileCopyrightText: 2022 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from typing import Optional

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def bill(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("vodafone.bill")

    is_vodafone = any(
        "\nRegistered address: Vodafone Limited, " in box for box in text_boxes
    )

    if not is_vodafone:
        return None

    account_holder_name = extract_account_holder_from_address(text_boxes[3])

    date_match = re.match(r"^([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})", text_boxes[0])
    assert date_match

    bill_date = dateparser.parse(date_match.group(1), languages=["en"])
    assert bill_date is not None

    return NameComponents(bill_date, "Vodafone", account_holder_name, "Bill")


@pdfrenamer
def bill_italy(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bill_italy")

    first_page = document[1]

    if "Vodafone per te\n" not in first_page:
        return None

    logger.debug("Possible Vodafone Italy Bill")

    account_holder_box = first_page.find_box_starting_with(
        "Intestatario del contratto\n"
    )
    account_holder = account_holder_box.split("\n")[1]

    details_faketable_idx = first_page.find_index_starting_with("Importo totale\n")
    details = build_dict_from_fake_table(
        first_page[details_faketable_idx], first_page[details_faketable_idx + 1]
    )

    date_box = details["Fattura non fiscale"]
    logger.debug(f"Vodafone Italy date box: {date_box!r}")
    _, date_str = date_box.split(" del ")
    date = dateparser.parse(date_str, languages=["it"])

    return NameComponents(date, "Vodafone", account_holder, "Fattura")
