# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from typing import Mapping


def build_dict_from_fake_table(fields_box: str, values_box: str) -> Mapping[str, str]:
    """Build a dictionary out of two boxes of a fake table.

    Fake tables are common in PDFs: two multi-line textboxes next to each other, one field
    per line. Parsing them is more than a bit annoying.
    """
    fields = fields_box.split("\n")
    values = values_box.split("\n")

    # Sometimes there are field names without values, or values without field names.
    # Ignore them.
    valid_fields_length = min(len(fields), len(values))
    return dict(zip(fields[:valid_fields_length], values[:valid_fields_length]))


def extract_account_holder_from_address(address: str) -> str:
    return address.split("\n", 1)[0].strip().title()
