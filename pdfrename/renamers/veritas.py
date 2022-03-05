# SPDX-FileCopyrightText: 2022 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import datetime
import logging

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def bolletta_2022(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bolletta_2022")

    first_page = document[1]

    if len(first_page) < 3:
        return None

    if "Veritas spa\nvia Brunacci 28\n" not in first_page[0]:
        return None

    logger.debug("Veritas bill detected")

    account_holder_box = first_page.find_box_starting_with("Intestatario contratto \n")
    logger.debug(f"Veritas account holder box: {account_holder_box!r}")
    account_holder = account_holder_box.split("\n")[1]

    details = first_page[2].split("\n")
    logger.debug(f"Veritas details: {details!r}")
    if not details[1].startswith("fattura n. "):
        return None

    bill_type = details[0].title()
    _, date_str = details[1].split(" del ", 1)
    logger.debug(f"Veritas date string: {date_str}")
    date = datetime.datetime.strptime(date_str, "%d.%m.%Y")

    return NameComponents(date, "Veritas", account_holder, "Bolletta", (bill_type,))
