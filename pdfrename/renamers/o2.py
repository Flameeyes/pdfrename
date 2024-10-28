# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def uk_copy_bill(document: pdf_document.Document) -> NameComponents | None:
    """Parse and rename copy bills from My O2 (UK) service.

    This applies to the archive of bills, rather than the original "My Bill"
    provided in the main landing page of billings.
    """
    text_boxes = document[1]

    if (
        len(text_boxes) < 2
        or "Telefónica UK Limited" not in text_boxes[-1]
        or text_boxes[0] != "Copy Bill\n"
    ):
        return None

    fields_box_index = text_boxes.find_index_starting_with("Account number\n")
    assert fields_box_index is not None

    bill_info = build_dict_from_fake_table(
        text_boxes[fields_box_index], text_boxes[fields_box_index + 1]
    )
    bill_date = dateparser.parse(bill_info["Bill date"], languages=["en"])
    assert bill_date is not None

    # Older bills have the fake table first, followed the address; newer bills use
    # a more complicated format, but the address is on the second box.
    if fields_box_index == 1:
        address_box = text_boxes[3]
    else:
        address_box = text_boxes[1]

    account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(
        bill_date,
        "O2 UK",
        account_holder_name,
        "Bill",
    )


@pdfrenamer
def uk_original_bill(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("uk_original_bill")

    text_boxes = document[1]

    if len(text_boxes) < 5:
        return None

    if not text_boxes[1].startswith("O2.co.uk/help | "):
        return None

    if (
        bill_info_keys_box := text_boxes.find_index_starting_with(
            "Account name\nAccount number\n"
        )
    ) is None:
        return None

    bill_info_keys = text_boxes[bill_info_keys_box]
    bill_info_values = text_boxes[bill_info_keys_box + 1]

    # Okay this is silly: sometimes the bill info values are split in two boxes.
    # so if there's not enough newlines, join it with the following box.
    if bill_info_values.count("\n") == 1:
        bill_info_values += text_boxes[bill_info_keys_box + 2]

    logger.debug(
        "Found likely O2 bill.\n  Bill info keys: %r\n  Bill info values: %r",
        bill_info_keys,
        bill_info_values,
    )

    bill_info = build_dict_from_fake_table(bill_info_keys, bill_info_values)

    if (account_holder_name := bill_info.get("Account name")) is None:
        logging.warning("Unable to find account holder name.")
        return None

    if (bill_date_str := bill_info.get("Bill date")) is None:
        logging.warning("Unable to find bill date.")
        return None

    # We assume by default that the document is a Bill, but O2 issues almost
    # identical Credit Note documents when paying outside of Direct Debit.
    document_type = "Bill"

    if "Credit Note\n" in text_boxes:
        document_type = "Credit Note"

    # O2 started issuing per-line bills, rather than one cumulative bill.
    # So append the line number if found.

    additional_components = []
    if billed_line_info := text_boxes.find_box_starting_with("Bill Summary for "):
        additional_components.append(
            billed_line_info[len("Bill Summary for ") :].strip()
        )

    bill_date = dateparser.parse(bill_date_str, languages=["en"])
    assert bill_date is not None

    return NameComponents(
        bill_date,
        "O2 UK",
        account_holder_name,
        document_type,
        additional_components=additional_components,
    )
