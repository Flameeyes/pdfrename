# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if not first_page:
        return None

    is_aws = first_page.find_box_starting_with("Amazon Web Services, Inc. Invoice\n")
    if not is_aws:
        is_aws = first_page.find_box_starting_with("Amazon Web Services Invoice\n")

    if not is_aws:
        return None

    fields_box = first_page.find_box_starting_with("Invoice Number:\n")
    assert fields_box
    fields_index = first_page.index(fields_box)

    # There's at least two versions of this, where the fields are either right after, or
    # once more after that. Try both.
    values_box = first_page[fields_index + 1]
    if fields_box.count("\n") != values_box.count("\n"):
        values_box = first_page[fields_index + 2]

    invoice_info = build_dict_from_fake_table(fields_box, values_box)

    invoice_date = dateparser.parse(invoice_info["Invoice Date:"], languages=["en"])
    assert invoice_date

    address_box = first_page.find_box_starting_with("Bill to Address:\n")
    assert address_box

    account_holder = address_box.split("\n")[1]
    assert account_holder.startswith("ATTN: ")

    account_holder = account_holder[6:]  # Drop the ATTN

    return NameComponents(invoice_date, "AWS", account_holder, "Invoice")


@pdfrenamer
def uk_vat_invoice(document: pdf_document.Document) -> NameComponents | None:
    first_page = document[1]
    if not first_page:
        return None

    if (
        first_page.find_box_starting_with("AMAZON WEB SERVICES EMEA SARL, UK BRANCH\n")
        is None
    ):
        return None

    details_box = first_page.find_box_starting_with("Account number:")
    assert details_box
    details = details_box.split("\n")
    account_number = details[1]
    account_holder = details[3]

    date_str = first_page[first_page.index("VAT Invoice Date:\n") + 4]
    date = dateparser.parse(date_str, languages=["en"])
    assert date

    invoice_number = first_page[first_page.index("VAT Invoice Number:\n") + 4]

    return NameComponents(
        date,
        "AWS",
        account_holder,
        "VAT Invoice",
        account_number=account_number,
        document_number=invoice_number.strip(),
    )
