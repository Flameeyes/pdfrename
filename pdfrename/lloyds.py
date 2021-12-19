# SPDX-FileCopyrightText: 2020 Svetlana Pantelejeva
#
# SPDX-License-Identifier: MIT

import re
from typing import Optional

import dateparser

from .lib.renamer import NameComponents, pdfrenamer
from .lib.utils import find_box_starting_with


@pdfrenamer
def statement(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("lloyds.statement")

    is_lloyds = any("logo, Lloyds Bank.\n" in box for box in text_boxes)

    if is_lloyds:
        document_requestor = find_box_starting_with(
            text_boxes, "Document requested by:\n"
        )

        account_holder_name = document_requestor.split("\n")[1]

        for box in text_boxes:
            date_match = re.search(
                r"^[0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}.\n)",
                box,
            )
            if date_match:
                break
        else:
            logger.debug("Unable to find the statement date.")

        assert date_match

        bill_date = dateparser.parse(date_match.group(1), languages=["en"])
        assert bill_date is not None

        return NameComponents(bill_date, "Lloyds", account_holder_name, "Statement")
