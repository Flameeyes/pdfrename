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

import dateparser
import pdfminer.high_level
import pdfminer.layout

import aws, chase, hounslow, hyperoptic, santander, scaleway
from components import NameComponents
from utils import (
    extract_account_holder_from_address,
    find_box_starting_with,
    build_dict_from_fake_table,
)

tool_logger = logging.getLogger("pdfrename")


def try_americanexpress(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("americanexpress")

    if text_boxes[0] != "www.americanexpress.co.uk\n":
        return None

    document_type = text_boxes[4].strip()
    if document_type == "Statement of Account":
        document_type = "Statement"

    account_holder_box = find_box_starting_with(text_boxes, "Prepared for\n")
    assert account_holder_box
    account_holder_index = text_boxes.index(account_holder_box)
    account_holder_name = account_holder_box.split("\n")[1].strip().title()

    # The date is the box after the Membership Number. We can't look for the one starting
    # with "Date" because there's more than one.
    membership_box = find_box_starting_with(text_boxes, "Membership Number\n")
    assert membership_box
    membership_index = text_boxes.index(membership_box)

    date_box = text_boxes[membership_index + 1]
    date_fields = date_box.split("\n")
    assert date_fields[0] == "Date"

    statement_date = datetime.datetime.strptime(date_fields[1], "%d/%m/%y")

    return NameComponents(
        statement_date, "American Express", account_holder_name, "Statement",
    )


def try_enel(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("enel")

    enel_address_box = find_box_starting_with(
        text_boxes, "Enel Energia - Mercato libero dell'energia\n"
    )
    if not enel_address_box:
        return None
    enel_address_index = text_boxes.index(enel_address_box)

    # Late 2019: the ENEL address is at the beginning, the address is two boxes before the
    # payment due date.
    due_date_box = find_box_starting_with(text_boxes, "Entro il ")
    assert due_date_box

    address_box_index = text_boxes.index(due_date_box) - 2
    address_box = text_boxes[address_box_index]

    # In 2020: the account holder address is _before_ the ENEL address. We can tell if we
    # got the wrong address box if it's too short in lines.
    if address_box.count("\n") < 2:
        address_box_index = enel_address_index - 1
        address_box = text_boxes[address_box_index]

    account_holder_name = extract_account_holder_from_address(address_box)

    # In 2018, the address was before the customer number instead, try again.
    if account_holder_name == "Periodo":
        customer_id_box = find_box_starting_with(text_boxes, "N° CLIENTE\n")
        assert customer_id_box
        customer_id_box_index = text_boxes.index(customer_id_box)

        address_box = text_boxes[customer_id_box_index - 1]
        account_holder_name = extract_account_holder_from_address(address_box)

    # The date follows the invoice number, look for the invoce number, then take the next.
    invoice_number_box = find_box_starting_with(text_boxes, "N. Fattura ")
    assert invoice_number_box

    date_box_index = text_boxes.index(invoice_number_box) + 1
    date_box = text_boxes[date_box_index]

    bill_date = datetime.datetime.strptime(date_box, "Del %d/%m/%Y\n")

    return NameComponents(bill_date, "ENEL Energia", account_holder_name, "Bolletta",)


def try_ms_bank(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("ms_bank")

    if "M&S Bank" not in text_boxes[-1]:
        return None

    account_name_box = find_box_starting_with(text_boxes, "Account Name\n")
    assert account_name_box

    account_holder_name = account_name_box.split("\n")[1].strip()

    # The statement period is just before the account name box.
    period_box_index = text_boxes.index(account_name_box) - 1
    period_line = text_boxes[period_box_index]

    logger.debug("found period specification %r", period_line)

    period_match = re.search(
        r"^[0-9]{2} [A-Z][a-z]+(?: [0-9]{4})? to ([0-9]{2} [A-Z][a-z]+ [0-9]{4})\n$",
        period_line,
    )
    assert period_match

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    return NameComponents(statement_date, "M&S Bank", account_holder_name, "Statement",)


def try_o2(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("o2")

    if "Telefónica UK Limited" not in text_boxes[-1]:
        return None

    assert text_boxes[0] == "Copy Bill\n"

    fields_box = text_boxes[1]
    values_box = text_boxes[2]

    bill_info = build_dict_from_fake_table(fields_box, values_box)
    bill_date = dateparser.parse(bill_info["Bill date"], languages=["en"])

    address_box = text_boxes[3]
    account_holder_name = extract_account_holder_from_address(address_box)

    return NameComponents(bill_date, "O2 UK", account_holder_name, "Bill",)


def try_tesco_bank(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("tesco_bank")

    # Before checking for statements, check other communications.
    if text_boxes[0].startswith("Tesco Bank\n") and any(
        box.startswith("Annual Summary of Interest\n") for box in text_boxes
    ):
        assert "Minicom:" in text_boxes[2]

        account_holder_name = text_boxes[4].strip()
        tax_year_line = [box for box in text_boxes if box.startswith("Tax Year:")]
        assert len(tax_year_line) == 1

        tax_year_match = re.search(
            r"^Tax Year: [0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n$",
            tax_year_line[0],
        )
        assert tax_year_match

        document_date = dateparser.parse(tax_year_match.group(1))

        return NameComponents(
            document_date,
            "Tesco Bank",
            account_holder_name,
            "Annual Summary of Interest",
        )

    if not any("tescobank.com/mmc" in box for box in text_boxes):
        return None

    assert "Current Account\n" in text_boxes[0]

    if text_boxes[1] == "Monthly statement\n":
        document_type = "Statement"
    else:
        document_type = text_boxes[1].strip().title()

    account_holder_name = extract_account_holder_from_address(text_boxes[2])

    fields_box = text_boxes[3]
    values_box = text_boxes[4]

    statement_info = build_dict_from_fake_table(fields_box, values_box)

    statement_date = dateparser.parse(
        statement_info["Statement date:"], languages=["en"]
    )

    return NameComponents(
        statement_date, "Tesco Bank", account_holder_name, document_type,
    )


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

    document_date = dateparser.parse(date_match.group(1), languages=["en"])

    address_box = text_boxes[5]
    account_holder_name = extract_account_holder_from_address(address_box)

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
        document_date, "Thames Water", account_holder_name, document_type,
    )


def try_soenergy(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("soenergy")

    is_soenergy = any(box == "www.so.energy\n" for box in text_boxes)
    if not is_soenergy:
        return None

    assert text_boxes[1] == "Hello, here is your statement.\n"

    # Find the account holder name at the start of the PDF.
    address_box = text_boxes[0]
    account_holder_name = extract_account_holder_from_address(address_box)

    period_line = text_boxes[2]
    logger.debug("found period specification: %r", period_line)
    period_match = re.match(
        r"^For the period of [0-9]{1,2} [A-Z][a-z]{2} [0-9]{4} - ([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})\n$",
        period_line,
    )
    assert period_match
    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    return NameComponents(
        statement_date, "So Energy", account_holder_name, "Statement",
    )


ALL_FUNCTIONS = (
    try_americanexpress,
    aws.try_aws,
    chase.try_chase,
    try_enel,
    hounslow.try_hounslow,
    hyperoptic.try_hyperoptic,
    try_ms_bank,
    try_o2,
    santander.try_santander,
    scaleway.try_scaleway,
    try_soenergy,
    try_tesco_bank,
    try_thameswater,
)


def find_filename(original_filename: str) -> Optional[str]:
    try:
        pages = list(pdfminer.high_level.extract_pages(original_filename))
    except pdfminer.pdfdocument.PDFTextExtractionNotAllowed:
        logging.warning("Unable to extract text from %s", original_filename)
        return None

    text_boxes = [
        obj.get_text()
        for obj in pages[0]
        if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal)
    ]

    if not text_boxes:
        tool_logger.warning(
            "No text boxes found on first page: %r", [list(page) for page in pages]
        )
        return None

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

    return None


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
        "--list_all",
        action="store_true",
        help="Whether to print checkmarks/question marks as comment next to files that are note being renamed.",
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
        new_basename = find_filename(original_filename)

        if new_basename is None:
            tool_logger.debug("No match for %s", original_filename)
            if args.list_all:
                print(f"# ? {original_filename}")
            continue

        dirname = os.path.dirname(original_filename)
        new_filename = os.path.join(dirname, new_basename)
        if new_filename == original_filename:
            if args.list_all:
                print(f"# ✓ {original_filename}")
            continue
        if args.rename:
            tool_logger.info("Renaming %s to %s", original_filename, new_filename)
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
