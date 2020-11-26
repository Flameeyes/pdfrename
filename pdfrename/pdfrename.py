# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import argparse
import datetime
import logging
import os
import re
import shutil
import warnings
from typing import Optional

import click
import dateparser
import pdfminer.high_level
import pdfminer.layout

import aws, azure, chase, digikey, edf, google, hounslow, hyperoptic, kbc, lloyds, mouser, natwest, nutmeg, payslips_facebook_uk, santander, scaleway, schwab, soenergy, thameswater, vodafone
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
        statement_date,
        "American Express",
        account_holder_name,
        "Statement",
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

    return NameComponents(
        bill_date,
        "ENEL Energia",
        account_holder_name,
        "Bolletta",
    )


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

    logger.debug(f"found period specification {period_line!r}")

    period_match = re.search(
        r"^[0-9]{2} [A-Z][a-z]+(?: [0-9]{4})? to ([0-9]{2} [A-Z][a-z]+ [0-9]{4})\n$",
        period_line,
    )
    assert period_match

    statement_date = dateparser.parse(period_match.group(1), languages=["en"])

    return NameComponents(
        statement_date,
        "M&S Bank",
        account_holder_name,
        "Statement",
    )


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

    return NameComponents(
        bill_date,
        "O2 UK",
        account_holder_name,
        "Bill",
    )


def try_tesco_bank(text_boxes, parent_logger) -> Optional[NameComponents]:
    logger = parent_logger.getChild("tesco_bank")

    # Before checking for statements, check other communications.
    if text_boxes[0].startswith("Tesco Bank\n") and find_box_starting_with(
        text_boxes, "Annual Summary of Interest\n"
    ):
        assert "Minicom:" in text_boxes[2]

        account_holder_name = text_boxes[4].strip()
        tax_year_line = find_box_starting_with(text_boxes, "Tax Year:")

        tax_year_match = re.search(
            r"^Tax Year: [0-9]{1,2} [A-Z][a-z]+ [0-9]{4} to ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})\n$",
            tax_year_line,
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
        statement_date,
        "Tesco Bank",
        account_holder_name,
        document_type,
    )


ALL_FUNCTIONS = (
    try_americanexpress,
    aws.try_aws,
    azure.try_azure,
    chase.try_chase,
    digikey.try_digikey,
    edf.try_edf,
    try_enel,
    google.try_google,
    hounslow.try_hounslow,
    hyperoptic.try_hyperoptic,
    kbc.try_kbc,
    lloyds.try_lloyds,
    mouser.try_mouser,
    natwest.try_ulster_bank,
    nutmeg.try_nutmeg,
    try_ms_bank,
    try_o2,
    payslips_facebook_uk.try_payslip_facebook_uk,
    santander.try_santander,
    scaleway.try_scaleway,
    schwab.try_schwab,
    soenergy.try_soenergy,
    try_tesco_bank,
    thameswater.try_thameswater,
    vodafone.try_vodafone,
)


def find_filename(original_filename: str) -> Optional[str]:
    try:
        pages = list(pdfminer.high_level.extract_pages(original_filename, maxpages=1))
    except pdfminer.pdfparser.PDFSyntaxError as error:
        tool_logger.warning(f"Invalid PDF file {original_filename}: {error}")
        return None

    text_boxes = [
        obj.get_text()
        for obj in pages[0]
        if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal)
    ]

    if not text_boxes:
        tool_logger.warning(
            f"No text boxes found on first page: {[list(page) for page in pages]!r}"
        )
        return None

    tool_logger.debug(f"textboxes: {text_boxes!r}")

    for function in ALL_FUNCTIONS:
        try:
            name = function(text_boxes, tool_logger)
            if name:
                return name.render_filename(True, True)
        except Exception:
            logging.exception(f"Function {function} failed on file {original_filename}")

    return None


@click.command()
@click.option(
    "--vlog",
    type=int,
    help="Python logging level. See the levels at https://docs.python.org/3/library/logging.html#logging-levels",
)
@click.option(
    "--rename/--no-rename",
    default=False,
    help="Whether to actually rename the files, or just output the rename commands.",
)
@click.option(
    "--list-all/--no-list-all",
    default=False,
    help="Whether to print checkmarks/question marks as comment next to files that are note being renamed.",
)
@click.argument(
    "input-files", nargs=-1, type=click.Path(exists=True, dir_okay=False, readable=True)
)
def main(*, vlog, rename, list_all, input_files):
    if vlog is not None:
        tool_logger.setLevel(vlog)
    logging.basicConfig()

    # Disable warnings on PDF extractions not allowed.
    warnings.filterwarnings("ignore", category=pdfminer.pdfdocument.PDFTextExtractionNotAllowedWarning)

    for original_filename in input_files:
        tool_logger.debug(f"Analysing {original_filename}")
        new_basename = find_filename(original_filename)

        if new_basename is None:
            tool_logger.debug(f"No match for {original_filename}")
            if list_all:
                print(f"# ? {original_filename}")
            continue

        dirname = os.path.dirname(original_filename)
        new_filename = os.path.join(dirname, new_basename)
        if new_filename == original_filename:
            if list_all:
                print(f"# ✓ {original_filename}")
            continue
        if rename:
            tool_logger.info(f"Renaming {original_filename} to {new_filename}")
            if os.path.exists(new_filename):
                logging.warning(f"File {new_filename} already exists, not overwriting.")
                continue
            if list_all:
                print(f"# {original_filename!r} → {new_filename!r}")
            shutil.move(original_filename, new_filename)
        else:
            print(f'ren "{original_filename}" "{new_filename}"')


if __name__ == "__main__":
    main()
