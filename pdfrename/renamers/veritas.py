# SPDX-FileCopyrightText: 2022 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import datetime
import logging
import re

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table

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

    details = first_page.find_box_with_match(lambda box: "\ncodice utente " in box)
    logger.debug(f"Veritas details: {details!r}")
    if not re.search(" n[.] [0-9]+", details):
        return None

    bill_type = details.split("\n", 1)[0].strip().title()
    date_str = re.search(r"del\s([0-9]{2}[.][0-9]{2}[.][0-9]{4})\n", details).group(1)
    logger.debug(f"Veritas date string: {date_str}")
    date = datetime.datetime.strptime(date_str, "%d.%m.%Y")

    return NameComponents(date, "Veritas", account_holder, "Bolletta", (bill_type,))


@pdfrenamer
def bolletta_idrico_2019(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bolletta_idrico_2019")

    try:
        last_page = document[4]
        if len(last_page) < 2:
            last_page = document[3]
    except IndexError:
        return None

    if not last_page.find_box_with_match(
        lambda box: (
            "\nSportello Online Veritas disponibile su\nwww.gruppoveritas.it" in box
            or "sportello\nonline di Veritas accessibile da\nwww.gruppoveritas.it"
            in box
            or "http://www.gruppoveritas.it/dove/centri-servizi.html" in box
        )
    ):
        return None

    logger.debug("Possible Veritas 2019 water bill found.")

    first_page = document[1]
    second_page = document[2]

    if len(first_page) < 3 or len(second_page) < 2:
        return None

    account_holder_box = second_page.find_box_starting_with("Fattura Intestata a:\n")
    logger.debug(f"Found account holder box: {account_holder_box!r}")
    if not account_holder_box:
        return None
    account_holder = account_holder_box.split("\n")[1]

    bill_type_box = first_page.find_box_starting_with("Fattura per la fornitura del")
    logger.debug(f"Found bill type box: {bill_type_box!r}")
    bill_type = (
        re.match("^Fattura per la fornitura del (.+) erogato in", bill_type_box)
        .group(1)
        .title()
    )

    details_faketable_idx = second_page.find_index_starting_with("N. Fattura\n")
    details = build_dict_from_fake_table(
        second_page[details_faketable_idx], second_page[details_faketable_idx + 1]
    )

    date_str = details["Emessa il"]
    date = datetime.datetime.strptime(date_str, ": %d.%m.%Y")

    return NameComponents(date, "Veritas", account_holder, "Bolletta", (bill_type,))


@pdfrenamer
def avviso_pagamento_rifiuti_2019(
    document: pdf_document.Document,
) -> NameComponents | None:
    logger = _LOGGER.getChild("avviso_pagamento_rifiuti_2019")

    try:
        last_page = document[4]
        if len(last_page) < 2:
            last_page = document[3]
    except IndexError:
        return None

    if not last_page.find_box_with_match(
        lambda box: (
            "Per  ulteriori  informazioni  visitare  il  sito  di  Veritas" in box
            or "Per ulteriori informazioni: www.gruppoveritas.it" in box
        )
    ):
        return None

    logger.debug("Possible Veritas 2019 refuse bill found.")

    first_page = document[1]
    second_page = document[2]

    if len(first_page) < 3 or len(second_page) < 2:
        return None

    account_holder_box = second_page.find_box_starting_with("Avviso Intestato a:\n")
    if not account_holder_box:
        return None
    account_holder = account_holder_box.split("\n")[1]

    bill_type_box = first_page.find_box_starting_with(
        "Le inviamo l' avviso di pagamento per il "
    )
    if not bill_type_box:
        logger.debug("Unable to detect bill type")
        return None
    bill_type = (
        # Note that the encoding is not UTF-8 compatible, so skip the accent!
        re.match(
            "Le inviamo l' avviso di pagamento per il (.+) di cui trover",
            bill_type_box,
        )
        .group(1)
        .title()
    )

    details_faketable_idx = second_page.find_index_starting_with("N. Avviso\n")
    details = build_dict_from_fake_table(
        second_page[details_faketable_idx], second_page[details_faketable_idx + 1]
    )

    date_str = details["Emesso il"]
    date = datetime.datetime.strptime(date_str, ": %d.%m.%Y")

    return NameComponents(
        date, "Veritas", account_holder, "Avviso di Pagamento", (bill_type,)
    )
