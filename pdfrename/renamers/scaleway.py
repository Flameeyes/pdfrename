# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re

import dateparser

from ..doctypes.en import INVOICE
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger("scaleway")


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("invoice")

    match document.creator:
        case b"Scaleway billing system":
            assert document.subject is not None
            try:
                subject = document.subject.decode("ascii")
            except UnicodeDecodeError:
                subject = document.subject.decode("utf-16")
        case b"\xfe\xff\x00S\x00c\x00a\x00l\x00e\x00w\x00a\x00y\x00 \x00b\x00i\x00l\x00l\x00i\x00n\x00g\x00 \x00s\x00y\x00s\x00t\x00e\x00m":
            assert document.subject is not None
            subject = document.subject.decode("utf-16")
        case _:
            return None

    if not subject.startswith("\n            Invoice\n"):
        return None

    invoice_number = subject.split("\n")[2].strip().lstrip("#")

    text_boxes = document[1]

    customer_box = text_boxes.find_box_starting_with("Customer \n")
    if customer_box:
        # Latest template
        account_holder = customer_box.split("\n")[1].strip()
    else:
        # Previous templates split this into two separate boxes.
        customer_label_idx = text_boxes.index("Customer\n")
        customer_box = text_boxes[customer_label_idx + 1]
        assert customer_box is not None
        account_holder = customer_box.strip()

    date_box = text_boxes.find_box_starting_with("Issued: \n")
    if date_box:
        # Latest template
        date_str = date_box.split("\n")[1].strip()
    else:
        # We need to find the Issued line that is mixed together with other items, so just
        # use regex to find it.
        for box in text_boxes:
            # We don't really use a strict regex here, but we do only extract the _date_
            # part rather than the time, which is also present but useless to the
            # renaming.
            date_match = re.search(
                r"Issued: ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}) at [0-9]", box
            )
            if date_match:
                break
        else:
            logger.debug("Unable to find the invoice issue date.")

        assert date_match
        date_str = date_match.group(1)

    bill_date = dateparser.parse(date_str)
    assert bill_date is not None

    return NameComponents(
        bill_date,
        "Scaleway",
        account_holder,
        INVOICE,
        document_number=invoice_number,
    )
