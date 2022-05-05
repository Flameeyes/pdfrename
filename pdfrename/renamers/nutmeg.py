# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import logging
from typing import Optional

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def suitability_report(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("suitability_report_2021")
    first_page = document[1]

    if (
        not first_page
        or len(first_page) < 4
        or "Suitability Report\n" not in first_page
    ):
        return None

    logger.debug("Possible Nutmeg Suitability Report found.")

    document_type_index = first_page.find_index_starting_with("Suitability Report\n")
    logger.debug(
        f"Nutmeg Suitability Report document type at index {document_type_index}"
    )
    if "\nNutmeg account number" not in first_page[document_type_index + 1]:
        logger.warning("Nutmeg Suitability Report without account number.")
        return None

    params_table = build_dict_from_fake_table(
        first_page[document_type_index + 1], first_page[document_type_index + 2]
    )

    report_date_str = params_table["Generated on:"]
    logger.debug(f"Nutmeg Suitability Report date: {report_date_str}")
    report_date = dateparser.parse(report_date_str, languages=["en"])

    account_holder_name = params_table["Produced for:"]

    second_page = document[2]
    if second_page and second_page[0] == "About your new pot\n":
        pot_name = second_page[1].strip()
        logger.debug(f"Suitability Report for a new pot: {pot_name}")
        additional_components = (pot_name,)
    else:
        additional_components = ()

    return NameComponents(
        report_date,
        "Nutmeg",
        account_holder_name,
        "Suitability Report",
        additional_components=additional_components,
    )


@pdfrenamer
def valuation_report(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("valuation_report")
    first_page = document[1]

    if (
        not first_page
        or len(first_page) < 5
        or first_page[-1] != "Produced by Nutmeg Saving and Investment Limited\n"
    ):
        return None

    if first_page[0] == "VALUATION REPORT\n":  # Late 2021
        date_str = first_page[2]
        account_holder = first_page[4]
    elif first_page[0].endswith(", this is your\nValuation Report\n"):  # 2018~2020
        date_str = first_page[1]
        account_holder = first_page[3]
    else:
        logger.debug(f"Unrecognized document starting with {first_page[0]}")
        return None

    logger.debug("Possible Nutmeg Valuation Report found.")

    if not date_str.startswith("As of ") and not date_str.startswith("As at "):
        logger.warning(f"Nutmeg Valuation Report with invalid date: {date_str}")

    date = dateparser.parse(date_str[6:], languages=["en"])

    return NameComponents(
        date,
        "Nutmeg",
        account_holder,
        "Valuation Report",
    )
