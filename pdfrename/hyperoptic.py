# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re
from typing import Optional, Sequence

from .components import NameComponents
from .lib.renamer import pdfrenamer
from .utils import build_dict_from_fake_table, find_box_starting_with


@pdfrenamer
def bill_2018(text_boxes, parent_logger) -> Optional[NameComponents]:
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
def bill(text_boxes, parent_logger) -> Optional[NameComponents]:
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
