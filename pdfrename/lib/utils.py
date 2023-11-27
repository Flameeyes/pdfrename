# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from collections.abc import Mapping, Sequence

_honorifics = {"mr", "mr.", "mrs", "ms", "miss"}


def drop_honorific(holder_name: str) -> str:
    try:
        split_honorific = holder_name.split(" ", 1)
        if split_honorific[0].lower() in _honorifics:
            return split_honorific[1]
    except Exception:
        pass

    return holder_name


def normalize_account_holder_name(name: str, do_drop_honorific: bool) -> str:
    # If there's trailing or heading spaces, just remove.
    name = name.strip()
    if do_drop_honorific:
        name = drop_honorific(name)

    # Some statements use all-upper-case names, default to title-casing them.
    if name.isupper():
        name = name.title()

    return name


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


def find_box_starting_with(text_boxes: Sequence[str], startswith: str) -> str | None:
    box = [box for box in text_boxes if box.startswith(startswith)]
    if not box:
        return None
    assert len(box) == 1
    return box[0]
