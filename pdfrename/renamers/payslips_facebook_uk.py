# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import datetime
import logging

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

_SERVICE = "Facebook UK Limited"


@pdfrenamer
def pre_adp_payslip(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("facebook.pre_adp_payslip")

    text_boxes = document[1]

    if len(text_boxes) < 5:
        return None

    if text_boxes[2] != "Facebook UK Ltd\n":
        return None

    logger.debug("Found Facebook Payslip")

    account_holder_name = extract_account_holder_from_address(text_boxes[1])

    date_box = text_boxes.find_box_starting_with("Date : ")
    assert date_box is not None

    payslip_date = dateparser.parse(date_box[7:], languages=["en"])
    assert payslip_date is not None

    return NameComponents(payslip_date, _SERVICE, account_holder_name, "Payslip")


@pdfrenamer
def pre_adp_p60(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if len(first_page) < 4:
        return None

    if (
        first_page[0] != "P60 End of Year Certificate\n"
        or "Facebook UK Ltd\n" not in first_page
    ):
        return None

    surname_label = first_page.index("Surname\n")
    assert (
        surname_label is not None
        and first_page[surname_label + 1] == "Forenames or initials\n"
    )

    surname = first_page[surname_label + 2]
    first_name = first_page[surname_label + 3]

    # To match the convention in the payslip.
    full_name = " ".join((first_name + surname).split())

    date_box = first_page.find_box_starting_with("Printed: ")
    assert date_box is not None

    date = datetime.datetime.strptime(date_box, "Printed: %d/%m/%Y %H:%M:%S\n")

    return NameComponents(date, _SERVICE, full_name, "P60")
