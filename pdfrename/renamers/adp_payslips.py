# SPDX-FileCopyrightText: 2022 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

# We're making an assumption here that the M08 I'm seeing on the current
# payslip is the _month_ (M08 in UK is November)
_ADP_PAYSLIP_CREATOR = re.compile(rb"Form ZF_XADP_M\d\d_PAYSLIP_NEW EN")


@pdfrenamer
def payslip_en(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("adp_payslips.payslip")

    creator = document.creator

    if creator is None or not _ADP_PAYSLIP_CREATOR.match(creator):
        return None

    logger.debug("Possible ADP-generated payslip.")

    text_boxes = document[1]

    details_box_index = text_boxes.find_index_starting_with(" Company Name :")
    if details_box_index is None:
        logger.debug("Unable to find box with details.")
        return None

    details_box = text_boxes[details_box_index]

    # The names are terminated by double whitespace.
    company_name_match = re.search("Company Name : (.+?)  +", details_box)
    if company_name_match is None:
        logger.debug("Unable to find company name.")
        return None
    company_name = company_name_match.group(1)

    date_match = re.search(r"Pay Date     : (\d{2}\.\d{2}\.\d{4})", details_box)
    if date_match is None:
        logger.debug("Unable to find pay date.")
        return None
    date = datetime.datetime.strptime(date_match.group(1), "%d.%m.%Y")

    # There's a "PRIVATE & CONFIDENTIAL" line first.
    _, address_box = text_boxes[details_box_index - 1].split("\n", 1)

    logger.debug(f"Found address box: {address_box!r}")
    employee_name = extract_account_holder_from_address(address_box)

    return NameComponents(date, company_name, employee_name, "Payslip")
