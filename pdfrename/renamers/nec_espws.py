# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT
#
# Implement tax bills emitted by https://www.necsws.com/revenues-benefits

import logging

import dateparser
from more_itertools import first

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import drop_honorific, extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

_KNOWN_COUNCILS = {"London Borough of Hounslow", "Milton Keynes City Council"}


@pdfrenamer
def tax_bill(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("tax_bill")

    try:
        first_page = document[1]

        possible_council = first(first_page[1].split("\n", 1))
    except IndexError:
        return None

    if possible_council not in _KNOWN_COUNCILS:
        return None

    subject = first_page[2]
    if not subject.startswith("Council Tax Bill "):
        logger.debug("Not a council tax bill, unknown format.")
        return None

    bill_date = dateparser.parse(first_page[0], languages=["en"])
    assert bill_date

    # In older bills, the subject box includes the address.
    if subject.count("\n") > 1:
        address_box = subject.split("\n", 1)[1]
    else:
        address_box = first_page[3]

    account_holder = extract_account_holder_from_address(address_box)
    # There can be more than one account holder, which makes things a bit more complicated.
    if "&" in account_holder:
        account_holders = [
            drop_honorific(holder.strip()) for holder in account_holder.split("&")
        ]
    else:
        account_holders = [account_holder]

    account_number_box = first_page.find_box_starting_with("Account Number")
    if account_number_box:
        account_number = account_number_box.split("\n")[1]

    return NameComponents(
        bill_date,
        possible_council,
        account_holders,
        "Council Tax Bill",
        account_number=account_number,
    )
