# SPDX-FileCopyrightText: 2025 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re

from ..doctypes.en import INVOICE
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, extract_account_holder_from_address

_SERVICE = "Andrews & Arnold"
_COMPANY_IDENTIFIER = "Andrews & Arnold Ltd\n"


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if _COMPANY_IDENTIFIER not in first_page or first_page[0] != "Sales\xa0Invoice\n":
        return None

    holder_address_idx = first_page.index(_COMPANY_IDENTIFIER) - 1
    holder_address = first_page[holder_address_idx].replace("\xa0", " ")

    account_holder = extract_account_holder_from_address(holder_address)

    details_idx = first_page.find_index_starting_with("Invoice\xa0Nº:")
    assert details_idx is not None
    details = build_dict_from_fake_table(
        first_page[details_idx].replace("\xa0", " "),
        first_page[details_idx + 1].replace("\xa0", " "),
    )

    if "Issued:" in details:
        invoice_date_str = details["Issued:"]
    else:
        invoice_date_str = details["Date (tax point):"]

    invoice_date = datetime.datetime.strptime(invoice_date_str, " %Y-%m-%d %H:%M:%S")

    invoice_number = details["Invoice Nº:"].strip()
    account_number = details["Account Nº:"].strip()

    return NameComponents(
        invoice_date,
        _SERVICE,
        account_holder,
        INVOICE,
        account_number=account_number,
        document_number=invoice_number,
    )


@pdfrenamer
def direct_debit_notice(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]

    if (
        _COMPANY_IDENTIFIER not in first_page
        or "Advance\xa0Notice\xa0of\xa0Direct\xa0Debit\xa0to\xa0be\xa0collected\xa0by\xa0Andrews\xa0&\xa0Arnold\xa0Ltd\n"
        not in first_page
    ):
        return None

    account_number_idx = first_page.find_index_starting_with("Account\xa0Nº")
    assert account_number_idx is not None

    account_number_match = re.match(
        r"Account\xa0Nº: (.+)\n", first_page[account_number_idx]
    )
    assert account_number_match is not None
    account_number = account_number_match.group(1)

    holder_address = first_page[account_number_idx + 1].replace("\xa0", " ")
    account_holder = extract_account_holder_from_address(holder_address)

    # This is technically not the date of the notice, but A&A does not include
    # the date on the notice at all. So we take the first day of the month
    # of when the direct debit should go out.
    # dateline = first_page.find_box_starting_with('Direct\xa0Debit\xa0Collection\xa0').replace("\xa0", " ")
    # date_match = re.search(r"on, or immediately after, (.+)\.\n", dateline)
    # assert date_match is not None

    # date_str = date_match.group(1)

    # NOTE: the dead code above is because something fails extracting the date.
    # So we instead throw this to the Epoch :(

    return NameComponents(
        datetime.datetime(1970, 1, 1),
        _SERVICE,
        account_holder,
        "Advance Notice of Direct Debit",
        account_number=account_number,
    )
