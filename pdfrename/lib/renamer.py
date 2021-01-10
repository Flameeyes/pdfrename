# SPDX-FileCopyrightText: 2021 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, List, Sequence, Optional

from .. import components

Boxes = Sequence[str]
Renamer = Callable[[Boxes, logging.Logger], Optional[components.NameComponents]]

ALL_RENAMERS: List[Renamer] = []


def pdfrenamer(func: Renamer) -> Renamer:
    ALL_RENAMERS.append(func)

    return func
