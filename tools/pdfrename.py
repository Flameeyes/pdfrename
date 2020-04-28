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

import pdfminer.high_level
import pdfminer.layout


def try_santander(text_boxes):

    is_santander_credit_card = any(
        box.get_text() == "Santander Credit Card \n" for box in text_boxes
    )

    if is_santander_credit_card:
        # Always include the account holder name, which is found in the second text box.
        account_holder_address = text_boxes[1].get_text()
        account_holder_name = account_holder_address.split("\n")[0].strip().title()

        period_line = [
            box.get_text()
            for box in text_boxes
            if box.get_text().startswith("Account summary as at:")
        ]
        assert len(period_line) == 1

        print(repr(period_line[0]))

        # Very annoying: the date is printed as "18th November 2019" -- which probably
        # would also mean "2nd" if the statement is earlier in the month.
        #
        # To workaround this, use two match groups and recompose the string to build up
        # with it.
        period_match = re.match(
            r"^Account summary as at: ([0-9]{2})[a-z]{2} ([A-Z][a-z]+ [0-9]{4}) for card number ending [0-9]{4}\n$",
            period_line[0],
        )
        assert period_match
        statement_date = datetime.datetime.strptime(
            f"{period_match.group(1)} {period_match.group(2)}", "%d %B %Y"
        )

        return f'{statement_date.strftime("%Y-%m-%d")} - Santander - {account_holder_name} - Credit Card - Statement.pdf'


def try_soenergy(text_boxes):
    is_soenergy = any(box.get_text() == "www.so.energy\n" for box in text_boxes)
    if not is_soenergy:
        return None

    assert text_boxes[1].get_text() == "Hello, here is your statement.\n"

    period_line = text_boxes[2].get_text()
    logging.debug("soenergy found period specification: %s", period_line)
    period_match = re.match(
        r"^For the period of [0-9]{1,2} [A-Z][a-z]{2} [0-9]{4} - ([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})\n$",
        period_line,
    )
    assert period_match
    statement_date = datetime.datetime.strptime(period_match.group(1), "%d %b %Y")

    return f'{statement_date.strftime("%Y-%m-%d")} - So Energy - Statement.pdf'


ALL_FUNCTIONS = (
    try_santander,
    try_soenergy,
)


def find_filename(original_filename, print_all_textboxes):
    first_page = next(pdfminer.high_level.extract_pages(original_filename, maxpages=1))

    text_boxes = [
        obj
        for obj in first_page
        if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal)
    ]

    if print_all_textboxes:
        print(text_boxes)

    for function in ALL_FUNCTIONS:
        name = function(text_boxes)
        if name:
            return name

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
        "--print_all_textboxes",
        action="store_true",
        help="Print all of the textboxes found on the first page, useful for development.",
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
    logging.basicConfig(level=args.vlog)

    for original_filename in args.input_files:
        dirname = os.path.dirname(original_filename)
        new_filename = os.path.join(
            dirname, find_filename(original_filename, args.print_all_textboxes)
        )
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
