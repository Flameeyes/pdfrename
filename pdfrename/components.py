# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dataclasses
import datetime

from typing import Optional, Sequence

_honorifics = {"mr", "mrs", "ms", "miss"}


def _drop_honorific(holder_name):
    try:
        split_honorific = holder_name.split(" ", 1)
        if split_honorific[0].lower() in _honorifics:
            return split_honorific[1]
    except Exception:
        pass

    return holder_name


@dataclasses.dataclass
class NameComponents:
    date: datetime.datetime
    service_name: str
    account_holder: Optional[str]
    additional_components: Sequence[str]

    def render_filename(
        self, include_account_holder: bool, drop_honorific: bool
    ) -> str:
        filename_components = []

        filename_components.append(self.date.strftime("%Y-%m-%d"))

        filename_components.append(self.service_name)

        if include_account_holder and self.account_holder:
            if drop_honorific:
                filename_components.append(_drop_honorific(self.account_holder))
            else:
                filename_components.append(self.account_holder)

        filename_components.extend(self.additional_components)

        return " - ".join(filename_components) + ".pdf"
