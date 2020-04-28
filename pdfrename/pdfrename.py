# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import argparse
import datetime
import logging
import os
import re
import shutil
import sys
from typing import Optional

import pdfminer.high_level
import pdfminer.layout

import hyperoptic, santander
from components import NameComponents

tool_logger = logging.getLogger("pdfrename")


def try_thameswater(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("thameswater")

    # There are at least two different possible boxes as the bottom of page 1 since 2017,
    # but they all include a link to TW's website.
    if "thameswater.co.uk/" not in text_boxes[-1]:
        return None

    assert text_boxes[0].startswith("Page 1 of ")

    date_line = text_boxes[1]
    date_match = re.search("^Date\n([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n", date_line)
    assert date_match

    document_date = datetime.datetime.strptime(date_match.group(1), "%d %B %Y")

    address_box = text_boxes[5]
    account_holder_name = address_box.split("\n", 1)[0].strip().title()

    document_subject = text_boxes[7]
    if (
        document_subject == "Your payment plan.\n"
        or document_subject == "Your new payment plan.\n"
    ):
        document_type = "Payment Plan"
    elif document_subject == "Your water and wastewater bill.\n":
        document_type = "Bill"
    else:
        document_type = "Other"

    return NameComponents(
        document_date, "Thames Water", account_holder_name, (document_type,)
    )


def try_soenergy(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("soenergy")

    is_soenergy = any(box == "www.so.energy\n" for box in text_boxes)
    if not is_soenergy:
        return None

    assert text_boxes[1] == "Hello, here is your statement.\n"

    # Find the account holder name at the start of the PDF.
    account_holder_name = text_boxes[0].split("\n", 1)[0].strip()

    period_line = text_boxes[2]
    logger.debug("found period specification: %r", period_line)
    period_match = re.match(
        r"^For the period of [0-9]{1,2} [A-Z][a-z]{2} [0-9]{4} - ([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})\n$",
        period_line,
    )
    assert period_match
    statement_date = datetime.datetime.strptime(period_match.group(1), "%d %b %Y")

    return NameComponents(
        statement_date,
        "So Energy",
        account_holder_name,
        additional_components=("Statement",),
    )


ALL_FUNCTIONS = (
    hyperoptic.try_hyperoptic,
    santander.try_santander,
    try_soenergy,
    try_thameswater,
)


def find_filename(original_filename):
    first_page = next(pdfminer.high_level.extract_pages(original_filename, maxpages=1))

    text_boxes = [
        obj.get_text()
        for obj in first_page
        if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal)
    ]

    tool_logger.debug("textboxes: %r", text_boxes)

    for function in ALL_FUNCTIONS:
        try:
            name = function(text_boxes, tool_logger)
            if name:
                return name.render_filename(True, True)
        except Exception:
            logging.exception(
                "Function %s failed on file %s", function, original_filename
            )

    return original_filename


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vlog",
        action="store",
        required=False,
        type=int,
        help=(
            "Python logging level. See the levels at "
            "https://docs.python.org/3/library/logging.html#logging-levels"
        ),
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="Whether to actually rename the files, or just output the rename commands.",
    )
    parser.add_argument(
        "input_files",
        action="store",
        type=str,
        nargs="+",
        help="One or more input filenames to try renaming.",
    )

    args = parser.parse_args()
    if args.vlog is not None:
        tool_logger.setLevel(args.vlog)
    logging.basicConfig()

    for original_filename in args.input_files:
        dirname = os.path.dirname(original_filename)
        new_filename = os.path.join(dirname, find_filename(original_filename))
        if new_filename == original_filename:
            continue
        if args.rename:
            logging.info("Renaming %s to %s", original_filename, new_filename)
            if os.path.exists(new_filename):
                logging.warning(
                    "File %s already exists, not overwriting.", new_filename
                )
                continue
            shutil.move(original_filename, new_filename)
        else:
            print(f'ren "{original_filename}" "{new_filename}"')


if __name__ == "__main__":
    main()
