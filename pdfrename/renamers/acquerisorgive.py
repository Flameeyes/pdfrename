# SPDX-FileCopyrightText: 2022 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import datetime
import logging
import re

from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer

_LOGGER = logging.getLogger(__name__)


@pdfrenamer
def bill(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("bill")

    first_page = document[1]

    # The bills are figure PDFs, so they need to be extracted manually.
    if (
        len(first_page) != 1
        or "istruzioni su www.acquerisorgive.it" not in first_page[0]
    ):
        return None

    logger.debug("Possible Avviso di Pagamento Acque Risorgive")

    account_holder_match = re.search(
        r"DATI INTESTATARIO PARTITA\s+([A-Z ]+)\s{3,}", first_page[0]
    )
    assert account_holder_match is not None
    account_holder = account_holder_match.group(1)

    date_match = re.search(r"A SALDO\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", first_page[0])
    assert date_match is not None
    date = datetime.datetime.strptime(date_match.group(1), "%d/%m/%Y")

    return NameComponents(
        date, "Acque Risorgive", account_holder, "Avviso di Pagamento"
    )
