# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import dataclasses
import datetime

from typing import Optional, Sequence

from . import utils


@dataclasses.dataclass
class NameComponents:
    date: datetime.datetime
    service_name: str
    account_holder: str
    document_type: str
    additional_components: Sequence[str] = ()

    def render_filename(
        self, include_account_holder: bool, drop_honorific: bool
    ) -> str:
        filename_components = []

        filename_components.append(self.date.strftime("%Y-%m-%d"))

        filename_components.append(self.service_name)

        if include_account_holder and self.account_holder:
            if drop_honorific:
                filename_components.append(utils.drop_honorific(self.account_holder))
            else:
                filename_components.append(self.account_holder)

        filename_components.append(self.document_type)

        filename_components.extend(self.additional_components)

        return " - ".join(filename_components) + ".pdf"
