# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import re
from typing import Optional, Sequence

from components import NameComponents
from utils import build_dict_from_fake_table


def _try_old_hyperoptic(text_boxes, logger) -> Optional[NameComponents]:
    if (
        text_boxes[0] == "www.hyperoptic.com\n"
        or text_boxes[0] == "www.hyperoptic.com \n"
    ):
        account_holder_box = text_boxes[1]
    elif text_boxes[7] == "www.hyperoptic.com \n":
        account_holder_box = text_boxes[0]
    else:
        return None

    logger.debug("looking for customer name in %r", account_holder_box)
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
    titles_str = [box for box in text_boxes if box.startswith("DD Ref:\n")]
    assert len(titles_str) == 1
    titles_idx = text_boxes.index(titles_str[0])
    values_str = text_boxes[titles_idx + 1]

    document_info = build_dict_from_fake_table(titles_str[0], values_str)
    bill_date_str = document_info["Invoice date:"]
    bill_date = datetime.datetime.strptime(bill_date_str, "%d %b %Y")

    return NameComponents(
        bill_date,
        "Hyperoptic",
        account_holder=account_holder_name,
        additional_components=("Bill",),
    )


def try_hyperoptic(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("hyperoptic")

    # Check for very old templates, used in 2017 to 2018.
    old_bill = _try_old_hyperoptic(text_boxes, logger)
    if old_bill:
        return old_bill

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
        account_holder=account_holder_name,
        additional_components=("Bill",),
    )
