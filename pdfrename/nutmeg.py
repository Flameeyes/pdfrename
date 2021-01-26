# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import dateparser

from typing import Optional

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .utils import build_dict_from_fake_table


@pdfrenamer
def suitability_report(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("nutmeg.suitability_report")

    if len(text_boxes) < 3:
        return None

    is_nutmeg = "\nNutmeg account number" in text_boxes[1]

    if is_nutmeg:
        assert text_boxes[0] == "Suitability Report\n"
        logger.debug("Found Nutmeg Suitability Report")

        params_table = build_dict_from_fake_table(text_boxes[1], text_boxes[2])

        report_date_str = params_table["Generated on:"]
        report_date = dateparser.parse(report_date_str, languages=["en"])

        account_holder_name = params_table["Produced for:"]

        return NameComponents(
            report_date, "Nutmeg", account_holder_name, "Suitability Report"
        )
