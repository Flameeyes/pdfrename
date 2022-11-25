# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import os
import shutil
import sys
import warnings

import click
import click_log
import pdfminer.high_level
import pdfminer.layout

from .lib.pdf_document import Document
from .lib.renamer import try_all_renamers
from .renamers import (  # noqa: F401
    acquerisorgive,
    americanexpress,
    aws,
    azure,
    chase,
    digikey,
    ebay,
    edf,
    enel,
    fineco,
    google,
    hounslow,
    hyperoptic,
    kbc,
    lloyds,
    mouser,
    ms_bank,
    natwest,
    newday,
    nutmeg,
    o2,
    octopus_energy,
    payslips_facebook_uk,
    santander,
    scaleway,
    schwab,
    soenergy,
    tesco_bank,
    thameswater,
    veritas,
    vodafone,
    xero,
)

tool_logger = logging.getLogger("pdfrename")
click_log.basic_config(tool_logger)


def find_filename(original_filename: str) -> str | None:
    try:
        document = Document(original_filename)
    except ValueError as e:
        tool_logger.warning(str(e))
        return None

    possible_names = list(try_all_renamers(document, tool_logger))

    if len(possible_names) > 1:
        logging.error(
            f"Unable to rename {original_filename}: multiple renamers matched."
        )
    elif possible_names:
        return possible_names[0].render_filename(True, True)

    return None


@click.command()
@click_log.simple_verbosity_option()
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
def main(*, rename, list_all, input_files):
    # Disable warnings on PDF extractions not allowed.
    warnings.filterwarnings(
        "ignore", category=pdfminer.pdfdocument.PDFTextExtractionNotAllowedWarning
    )

    for original_filename in input_files:
        try:
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
                    tool_logger.warning(
                        f"File {new_filename} already exists, not overwriting."
                    )
                    continue
                if list_all:
                    print(f"# {original_filename!r} → {new_filename!r}")
                shutil.move(original_filename, new_filename)
            else:
                print(f'ren "{original_filename}" "{new_filename}"')
        except:  # noqa: E722
            tool_logger.exception(f"While processing {original_filename}: ")
            sys.exit(-1)


if __name__ == "__main__":
    main()
