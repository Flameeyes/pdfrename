<!--
SPDX-FileCopyrightText: 2020 Diego Elio Pettenò

SPDX-License-Identifier: MIT
-->

# PDF Renaming Utilities

This is a rough and hacky script that looks into the first page of PDF files to figure out
what they are, and propose (or applies) a new name to them based on their content.

## Supported PDFs

As this is aimed at my (@Flameeyes) own use, the list of supported PDFs pretty much
focuses on bills and statements from UK, Italian, or Irish services and banks.

- [American Express UK](https://www.americanexpress.com/uk/)
- [Microsoft Azure](https://azure.microsoft.com/)
  - Invoices
- [Chase](https://www.chase.com/)
- [Digikey](https://www.digikey.com/)
  - Invoices
- [eBay](https://www.ebay.com/)
  - Seller Statements (Detailed and Summarized)
- [EDF Energy](https://www.edfenergy.com/)
  - Bills
- [ENEL Energia](https://www.enel.it/)
- [FinecoBank](https://finecobank.co.uk/)
  - UK Bank Statements
- [Google Cloud](https://cloud.google.com)
  - Invoices (European)
- [London Borough of Hounslow](https://www.hounslow.gov.uk/)
  - Council Tax Bills
- [Hyperoptic](https://www.hyperoptic.com/)
  - Bills (templates from 2017 to 2020)
- [KBC Ireland](https://wwww.kbc.ie/)
  - Statements ca. 2015
- [Lloyds](https://www.lloydsbank.com/)
- [M & S Bank](https://bank.marksandspencer.com/)
- [Mouser](https://www.mouser.com/)
  - Invoices
- NatWest Group
  - [NatWest](https://nwolb.com/)
    - Statements
    - Statements of Fees
    - Certificate of Interest
  - [Ulster Bank NI](https://digital.ulsterbank.co.uk/)
    - Statements
    - Statements of Fees
    - Certificate of Interest (Untested)
- NewDay Cards
  - Amazon Platinum MasterCard Statements
- [Nutmeg](https://www.nutmeg.com/)
  - Suitability Reports
- [O2 UK](https://www.o2.co.uk/)
  - Bills
- [Octopus Energy](https://octopus.energy/)
- [Santander UK](https://www.santander.co.uk)
  - Select Current Account Statements
  - 1|2|3 Current Account Statements
  - Statements of Fees
  - Credit Card Statements
  - Credit Card Annual Statements
- [Scaleway](https://www.scaleway.com/)
  - Tested with English invoices only.
- [So Energy](https://www.so.energy/)
  - Statement
  - Final Bill
  - Annual Summary
- [Thames Water](https://www.thameswater.co.uk/)
  - Bills
  - Payment Plans
  - Letters
- [Tesco Bank](https://www.tescobank.com/)
- [TSB](https://www.tsb.co.uk/) Statements
- [Veritas](https://gruppoveritas.it/)
  - Bills
- [Vodafone UK](https://www.vodafone.co.uk/)
  - Bills

## Usage

This project uses [uv](https://docs.astral.sh/uv/). Dependencies and a suitable Python
are installed automatically on first run, so you can run the script from the checkout and
point it to one or more PDFs:

```
# Only prints suggested renames
$ uv run pdfrename unsortedbill.pdf

# Actually rename files
$ uv run pdfrename --rename unsortedbill.pdf
```

To install it as a standalone tool instead, use `uv tool install .` and run `pdfrename`
directly.

## Development

```
$ uv sync                        # create .venv with the dev dependency group
$ uv run pytest --mypy           # type checks
$ uvx pre-commit run --all-files # ruff, reuse, etc.
```
