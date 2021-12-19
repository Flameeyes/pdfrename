# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import dataclasses
import datetime

from typing import Sequence

from . import utils


def _normalize_account_holder_name(name: str, drop_honorific: bool) -> str:
    # If there's trailing or heading spaces, just remove.
    name = name.strip()
    if drop_honorific:
        name = utils.drop_honorific(name)

    # Some statements use all-upper-case names, default to title-casing them.
    if name.isupper():
        name = name.title()

    return name


@dataclasses.dataclass
class NameComponents:
    date: datetime.datetime
    service_name: str
    account_holder: str | Sequence[str]
    document_type: str
    additional_components: Sequence[str] = ()

    @property
    def account_holders(self) -> Sequence[str]:
        if isinstance(self.account_holder, str):
            return (self.account_holder,)
        else:
            return self.account_holder

    def render_filename(
        self, include_account_holder: bool, drop_honorific: bool
    ) -> str:
        filename_components = []

        filename_components.append(self.date.strftime("%Y-%m-%d"))

        filename_components.append(self.service_name)

        if include_account_holder and self.account_holder:
            account_holder = " & ".join(
                _normalize_account_holder_name(name, drop_honorific)
                for name in self.account_holders
            )

            filename_components.append(account_holder)

        filename_components.append(self.document_type)

        filename_components.extend(self.additional_components)

        return " - ".join(filename_components) + ".pdf"
