# SPDX-FileCopyrightText: 2020 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import importlib
import pkgutil


def load_all_renamers() -> None:
    for renamer_module in pkgutil.walk_packages(__path__):
        importlib.import_module(f"{__name__}.{renamer_module.name}")
