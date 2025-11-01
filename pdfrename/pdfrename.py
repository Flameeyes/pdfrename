# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import click
import click_log
from more_itertools import only

from .lib.pdf_document import Document
from .lib.renamer import try_all_renamers
from .lib.utils import apply_pdfminer_log_filters
from .renamers import load_all_renamers

tool_logger = logging.getLogger("pdfrename")
click_log.basic_config(tool_logger)


class MultipleRenamersError(ValueError):
    pass


def find_filename(original_filename: Path) -> Path | None:
    try:
        document = Document(original_filename)
    except ValueError as e:
        tool_logger.warning(str(e))
        return None

    try:
        if name := only(try_all_renamers(document), too_long=MultipleRenamersError):
            return name.render_filename()

    except MultipleRenamersError:
        logging.error(
            f"Unable to rename {original_filename}: multiple renamers matched."
        )

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
    "input-files",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
def main(*, rename: bool, list_all: bool, input_files: Sequence[Path]):
    apply_pdfminer_log_filters()
    load_all_renamers()

    for original_filename in input_files:
        try:
            tool_logger.debug(f"Analysing {original_filename}")

            if not (new_basename := find_filename(original_filename)):
                tool_logger.debug(f"No match for {original_filename}")
                if list_all:
                    print(f"# ? {original_filename}")
                continue

            new_filename = original_filename.parent / new_basename
            if new_filename == original_filename:
                if list_all:
                    print(f"# ✓ {original_filename}")
                continue
            if rename:
                tool_logger.info(f"Renaming {original_filename} to {new_filename}")
                if new_filename.exists():
                    tool_logger.warning(
                        f"File {new_filename} already exists, not overwriting."
                    )
                    continue
                if list_all:
                    print(f"# {original_filename!r} → {new_filename!r}")
                original_filename.replace(new_filename)
            else:
                print(f'ren "{original_filename}" "{new_filename}"')
        except:  # noqa: E722
            tool_logger.exception(f"While processing {original_filename}: ")
            sys.exit(-1)


if __name__ == "__main__":
    main()
