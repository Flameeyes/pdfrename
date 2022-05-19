# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

import dateparser

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import build_dict_from_fake_table, find_box_starting_with

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def bill_2018(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("hyperoptic.bill_2018")

    if (
        text_boxes[0] == "www.hyperoptic.com\n"
        or text_boxes[0] == "www.hyperoptic.com \n"
    ):
        account_holder_box = text_boxes[1]
    elif len(text_boxes) > 8 and text_boxes[7] == "www.hyperoptic.com \n":
        account_holder_box = text_boxes[0]
    else:
        return None

    logger.debug(f"looking for customer name in {account_holder_box!r}")
    account_holder_match = re.search(r"Customer Name: ([^\n]+)\n", account_holder_box)
    assert account_holder_match
    account_holder_name = account_holder_match.group(1)

    # Extract the bill date from a "fake table".
    #
    # Older (2017~2018) Hyperoptic bills have two multi-line text boxes, one including all
    # the labels, and the other including all of the values.
    #
    # They thankfully sit next to each other, so once one is found, it's possible to find
    # the invoice date with relative ease.
    titles_str = find_box_starting_with(text_boxes, "DD Ref:\n")
    assert titles_str

    titles_idx = text_boxes.index(titles_str[0])
    values_str = text_boxes[titles_idx + 1]

    document_info = build_dict_from_fake_table(titles_str, values_str)
    bill_date_str = document_info["Invoice date:"]
    bill_date = datetime.datetime.strptime(bill_date_str, "%d %b %Y")

    return NameComponents(
        bill_date,
        "Hyperoptic",
        account_holder_name,
        "Bill",
    )


@pdfrenamer
def bill_2020(text_boxes, parent_logger) -> NameComponents | None:
    logger = parent_logger.getChild("hyperoptic.bill")

    # All Hyperoptic objects on the page are logos, not text. But Hypernews is fairly
    # specific, too.
    is_hyperoptic = "Hypernews\n" in text_boxes

    # Older templates of the bills don't have "Hypernews", so we need to guess. If there's
    # a "DD Ref" field, and the following includes HYP, it's probably Hyperoptic.
    if not is_hyperoptic and "DD Ref:\n" in text_boxes:
        dd_ref_idx = text_boxes.index("DD Ref:\n")
        dd_ref = text_boxes[dd_ref_idx + 1]
        is_hyperoptic = "HYP" in dd_ref

    if not is_hyperoptic:
        return None

    account_idx = text_boxes.index("Name:\n")
    account_holder_name = text_boxes[account_idx + 1].strip()

    date_idx = text_boxes.index("Bill date:\n")
    date_str = text_boxes[date_idx + 1]

    bill_date = datetime.datetime.strptime(date_str, "%d %b %Y\n")

    return NameComponents(
        bill_date,
        "Hyperoptic",
        account_holder_name,
        "Bill",
    )


@pdfrenamer
def bill_2021(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bill_2021")

    text_boxes = document[1]

    if not "Here's your latest bill from Hyperoptic.\n" in text_boxes:
        return None

    account_holder_name = text_boxes[0].strip()

    # Depending on when the bill was generated, the details column includes the following:
    # ['Your dates\n', 'Bill date:\n', 'Payment date:\n', 'Your account details\n',
    #  'Account number:\n', 'Bill number:\n', 'Our details\n']
    # And this is not _quite_ a fake table, because of the three headers in there.
    # But ont he other hand, there's newer generated bills that have an actual fake table,
    # so look for the distance between the two possible fields.
    bill_date_header_idx = text_boxes.index("Bill date:\n")
    payment_date_header_idx = text_boxes.index("Payment date:\n")
    account_details_idx = text_boxes.index("Your account details\n")
    logger.debug(
        f"Bill date header at index {bill_date_header_idx}, payment date header at index {payment_date_header_idx}"
    )

    if payment_date_header_idx == bill_date_header_idx + 2:
        bill_date_string = text_boxes[bill_date_header_idx + 1]
    elif account_details_idx == payment_date_header_idx + 1:
        bill_date_string = text_boxes[bill_date_header_idx + 6]
    else:
        bill_date_string = text_boxes[payment_date_header_idx + 1]
    bill_date = dateparser.parse(bill_date_string, languages=["en"])
    assert bill_date

    return NameComponents(bill_date, "Hyperoptic", account_holder_name, "Bill")
