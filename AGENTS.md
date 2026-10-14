<!--
SPDX-FileCopyrightText: 2026 Diego Elio Pettenò

SPDX-License-Identifier: 0BSD
-->

# AGENTS.md

How this project works, and how to add a new renamer when someone gives you a few
sample PDFs.

## What the tool does

`pdfrename` opens each PDF passed on the command line, extracts the text boxes on the
first page (and on later pages if a renamer asks for them), and runs every registered
**renamer** against it. A renamer either recognises the document and returns its
`NameComponents` (date, service, holder, type, …), or returns `None`. If exactly one
renamer matches, the tool proposes (or, with `--rename`, applies) a filename like:

```
2025-02-01 - Hetzner - Jane Doe - Invoice - R0012345678.pdf
```

Most documents are bills, invoices and statements from UK, Italian and Irish services.

## Layout

| Path | Purpose |
| --- | --- |
| `pdfrename/pdfrename.py` | Click CLI (`main`) and `find_filename()`. Errors out on a file if more than one renamer matches. |
| `pdfrename/lib/pdf_document.py` | `Document` (wraps pdfminer; 1-indexed pages via `document[n]`, PDF metadata) and `PageTextBoxes` (list-like page content with search helpers). |
| `pdfrename/lib/renamer.py` | `NameComponents`, the `@pdfrenamer` registration decorator, `try_all_renamers()`. |
| `pdfrename/lib/utils.py` | `build_dict_from_fake_table()`, `extract_account_holder_from_address()`, `normalize_account_holder_name()`, pdfminer log filters. |
| `pdfrename/lib/itext.py` | `did_itext_generate(document)`: checks whether the Producer is iText. |
| `pdfrename/doctypes/en.py` | Shared document-type strings (`INVOICE`, `STATEMENT`, `CREDIT_CARD_STATEMENT`, …). |
| `pdfrename/renamers/*.py` | One module per service. All of them are imported automatically by `load_all_renamers()` (`pkgutil.walk_packages`), so you don't need to register a new module anywhere. |

## Tooling

The project uses [uv](https://docs.astral.sh/uv/) and requires Python 3.12 or later.

```bash
uv sync
```

```bash
uv run pdfrename path/to/file.pdf
```

```bash
uv run pytest --mypy
```

```bash
uvx pre-commit run --all-files
```

- `uv run pdfrename FILE...` is a dry run: it prints `ren "old" "new"` lines for matches.
  It renames only with `--rename`. Use `--list-all` to also print `# ?` for files with
  no match and `# ✓` for files whose name is already right.
- `uv run pytest --mypy` is the test suite. Right now it only type-checks with mypy.
  CI runs it on Linux, Windows and macOS.
- pre-commit runs ruff check + format (line length 88, isort rules), REUSE licence
  checks and whitespace fixers. **Every new file needs an SPDX header** (see the
  existing renamers), or the `reuse` hook will fail.

## Seeing what is inside a PDF

You can't write a renamer without knowing the exact strings pdfminer extracts. There are
two ways to see them.

### 1. `-v DEBUG` on the CLI

```bash
uv run pdfrename -v DEBUG sample.pdf
```

`-v`/`--verbosity` takes a level name (`CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`).
It isn't a counter, so `-vv` doesn't work. The log goes to **stderr**, one line per
message, each starting with `debug:`. The lines you care about are:

```
debug: Analysing sample.pdf
debug: sample.pdf: page 1 is beyond the extracted pages, extracting now.
debug: sample.pdf p1: ['ACME Widgets Ltd\nInvoice No: 1234\n', 'Invoice date: 01/02/2025\n']
debug: sample.pdf: extracted info {'Producer': b'Example Producer 1.0', 'CreationDate': b'D:20250201120000Z'}
debug: No match for sample.pdf
```

- The `pN: [...]` line is the Python `repr()` of the list of text boxes for page N. Each
  element is one box, i.e. one item of `document[N]`. **The strings in your code must
  match these reprs exactly**, including trailing `\n`, `\xa0` (non-breaking spaces),
  doubled spaces, `’` vs `'`, and so on.
- `extracted info {...}` is the PDF metadata dictionary (Producer, Creator, Author,
  Title, Subject, CreationDate). It is logged only when some renamer reads metadata.
  That happens on every run today, but don't rely on it. Use the script below if you
  need it for sure.
- Pages after the first are extracted and logged only when some existing renamer asks
  for them. Your new renamer may need pages that don't appear in this log.
- Other `debug:` lines come from existing renamers probing the file (e.g. "possible
  NewDay statement."). That is normal. A traceback logged as `renamer <function …>
  failed` means some renamer raised an exception on this file. If it's an existing
  renamer, check whether your sample is triggering an `assert` in it (see
  "Avoiding false matches" below).

To save it all to a file:

```bash
uv run pdfrename -v DEBUG sample1.pdf sample2.pdf 2> dump.txt
```

### 2. An indexed dump with a script

Renamers often go by index (`first_page[idx + 1]`), so a numbered dump is easier to
work with. Pass the file, then the pages you want (default: page 1):

```bash
uv run python -c "
import sys
from pathlib import Path
from pdfrename.lib.pdf_document import Document
doc = Document(Path(sys.argv[1]))
print('producer:', doc.producer, 'creator:', doc.creator, 'author:', doc.author,
      'title:', doc.title, 'subject:', doc.subject, 'created:', doc.creation_date)
for page in map(int, sys.argv[2:] or ['1']):
    for idx, box in enumerate(doc[page]):
        print(f'p{page}[{idx}]: {box!r}')
" sample.pdf 1 2
```

Output:

```
producer: b'Example Producer 1.0' creator: None author: None title: None subject: None created: 2025-02-01 12:00:00
p1[0]: 'ACME Widgets Ltd\nInvoice No: 1234\n'
p1[1]: 'Invoice date: 01/02/2025\n'
```

Run it on **every** sample and compare the outputs side by side before you write any
code.

### How to read text boxes

- A box is one pdfminer `LTTextBoxHorizontal`. A box often holds several lines joined
  by `\n`, and it almost always ends with `\n`.
- Box order is pdfminer's layout order, which is not always the visual reading order.
  Two-column "fake tables" (labels in one box, values in the next) are very common.
  `build_dict_from_fake_table(labels_box, values_box)` zips them line by line into a
  dict.
- The same template can split boxes differently from one month to the next, especially
  after the issuer redesigns their documents. Indexes such as `first_page[2]` are
  fragile. Prefer finding an anchor box by content, then moving relative to it.
- If a page is a single figure (scanned or flattened PDFs), `Document` falls back to
  `extract_text()`, so the page becomes **one** big box. If `document[1]` is empty, the
  PDF has no text layer, and this tool can't handle it (there's no OCR).
- Metadata values (`document.producer`, `.creator`, `.author`, `.title`, `.subject`)
  are **`bytes`**, or `None` if absent. Compare them against `b"..."` literals.
  `document.creation_date` is a parsed `datetime` or `None`.

## The renamer contract

```python
RenamerV2 = Callable[[pdf_document.Document], NameComponents | None]
```

- Decorate the function with `@pdfrenamer`. The function name only matters for logs.
  One module can define several renamers (e.g. one per template year or document type).
- **Every renamer runs on every PDF.** Do the cheap, specific identification check
  first, and return `None` right away if it fails.
- Return `None` when the document isn't yours. Once you're sure it **is** yours,
  `assert` on anything that must be there. An exception is caught and logged with a
  traceback by `try_all_renamers()`, and that file gets no rename. This is the
  preferred way to surface "this is ours but the layout changed".
- If two renamers match the same file, the tool refuses to rename it ("multiple
  renamers matched"). Make identification specific enough not to collide with other
  modules.

`NameComponents` fields, in filename order:

| Field | Type | Notes |
| --- | --- | --- |
| `date` | `datetime.datetime` | Rendered as `YYYY-MM-DD`. Use the document/issue/statement-end date. |
| `service_name` | `str` | Human-facing brand name (`"Santander"`, `"Octopus Energy"`). Keep it in a module-level constant. |
| `account_holder` | `str` or `Sequence[str]` | Normalised: surrounding whitespace stripped, honorifics (Mr/Mrs/Ms/Miss) dropped, ALL-CAPS title-cased. Multiple holders are joined with ` & `. Empty means it is skipped. |
| `document_type` | `str` | Use a constant from `doctypes/en.py` when one fits, or a string in the document's language (e.g. `"Bolletta"`). |
| `account_number` | `str \| None` | Optional. |
| `document_number` | `str \| None` | Optional; `/` becomes `-`. |

`render_filename()` joins the fields with `" - "`, adds `.pdf`, and raises
`InvalidFilenameError` if the result contains `:`, `/`, `\` (or is otherwise reserved
on Windows). Strip or replace such characters in extracted values.

### `PageTextBoxes` helpers (`document[n]`)

`len()`, indexing, iteration and `in` work like on a list. `"Exact box\n" in page` tests
for a **whole box**, not a substring. For substrings use
`any("needle" in box for box in page)`. Also available:

- `page.index(box_text)`: index of an exact box (raises `ValueError` if missing).
- `page.find_box_starting_with(prefix)` / `page.find_index_starting_with(prefix)`
- `page.find_box_with_match(predicate)` / `page.find_index_with_match(predicate)`
- `page.find_all_matching_regex(compiled_re)`: yields `re.Match` objects (uses
  `pattern.match`, so the match is anchored at the start of the box).
- `page.find_all_indexes_matching_regex(compiled_re)`

⚠️ The `find_*` helpers return `None` when nothing matches, but **raise `ValueError` when
more than one box matches**, because they use `more_itertools.only`. Choose prefixes that
are unique on the page.

`document[n]` raises `IndexError` if the page doesn't exist. Wrap it in
`try`/`except IndexError: return None` when the extra page is part of identification,
and only ask for page 2+ **after** the page-1 checks have passed.

### Dates

- Fixed format: `datetime.strptime(s, "%d/%m/%Y\n")`. Include the trailing `\n` (or
  `.strip()` first).
- Free-form or localised: `dateparser.parse(s, languages=["en"])` (or `["it"]`), then
  `assert date is not None`.
- Last resort: `document.creation_date` (used by `hl.py`).

## Writing a new renamer from samples

1. **Dump every sample** with the indexed script (page 1, plus page 2 if page 1 looks
   thin). Note which boxes are identical across samples and which ones change.
2. **Choose identification anchors**: strings that appear in every sample of this
   document type and nowhere else. Good ones are the legal entity name with its
   address line (`"Andrews & Arnold Ltd\n"`), a document title box, or a distinctive
   `producer`/`creator`/`title` metadata value (`natwest.py`, `fiserv.py`,
   `octopus_energy.py`). Combine two anchors if one alone is generic. Avoid
   `"Invoice\n"` on its own.
3. **Locate the fields** (date, holder, account/document number) relative to anchor
   boxes. Use regexes with named groups for multi-line boxes, and
   `build_dict_from_fake_table` for label/value box pairs. For the holder, the first
   line of the address block via `extract_account_holder_from_address()` is the usual
   choice.
4. **Handle variants.** If the samples come from different template versions, write
   one renamer per template (`bill_2021`, `bill_2023`, as in `enel.py`), or loop over a
   tuple of regexes (as in `octopus_energy.py`).
5. **Create `pdfrename/renamers/<service>.py`** (snake_case) from the template below.
6. **Verify**:
   - `uv run pdfrename --list-all -v DEBUG sample*.pdf 2> dump.txt`: every sample
     prints one `ren` line with the expected name, and there are no
     `renamer … failed` tracebacks or "multiple renamers matched" errors in
     `dump.txt`.
   - If other PDFs are available (e.g. ones another renamer already handles), run on
     them too and check that your renamer doesn't match them.
   - `uv run pytest --mypy` and `uvx pre-commit run --all-files` both pass.
7. **Add the service to the "Supported PDFs" list in `README.md`** (alphabetical, with
   the document types covered).

### Template

```python
# SPDX-FileCopyrightText: 2026 Diego Elio Pettenò
#
# SPDX-License-Identifier: MIT

import logging
import re
from datetime import datetime

from ..doctypes.en import INVOICE
from ..lib import pdf_document
from ..lib.renamer import NameComponents, pdfrenamer
from ..lib.utils import extract_account_holder_from_address

_LOGGER = logging.getLogger(__name__)

_SERVICE = "Example Co"
_COMPANY_IDENTIFIER = "Example Co Ltd, 1 High Street, London\n"

_INVOICE_DETAILS_RE = re.compile(
    r"^Invoice number: (?P<number>[A-Z0-9-]+)\nInvoice date: (?P<date>\d{2}/\d{2}/\d{4})\n"
)


@pdfrenamer
def invoice(document: pdf_document.Document) -> NameComponents | None:
    logger = _LOGGER.getChild("invoice")
    first_page = document[1]

    # Cheap, specific identification first.
    if _COMPANY_IDENTIFIER not in first_page:
        return None

    logger.debug("Found likely Example Co invoice.")

    # From here on this is ours: assert rather than silently returning None.
    details_match = next(first_page.find_all_matching_regex(_INVOICE_DETAILS_RE), None)
    assert details_match is not None, "invoice details box not found"

    invoice_date = datetime.strptime(details_match.group("date"), "%d/%m/%Y")

    address_idx = first_page.index(_COMPANY_IDENTIFIER) + 1
    account_holder = extract_account_holder_from_address(first_page[address_idx])

    return NameComponents(
        invoice_date,
        _SERVICE,
        account_holder,
        INVOICE,
        document_number=details_match.group("number"),
    )
```

Good existing examples to copy from:

- `aaisp.py`: a company anchor plus a fake table, with `\xa0` handling.
- `hetzner.py`: a short and simple renamer.
- `octopus_energy.py`: metadata-based identification and several regex variants.
- `santander.py`: multiple renamers per module, joint account holders, page 2.
- `enel.py`, `windtre.py`, `veritas.py`: Italian documents and per-year templates.
- `hl.py`: falls back to `document.creation_date`.

## Conventions

- One module per service, named in snake_case after the service. The SPDX header is
  MIT for code, with the copyright holder and year.
- Module-level constants for the service name and identifiers. Compile regexes at
  module level.
- `_LOGGER = logging.getLogger(__name__)`, and `logger = _LOGGER.getChild("<renamer>")`
  inside each renamer. Log identification steps at `debug`.
- Type-annotate everything (`-> NameComponents | None`). mypy runs in CI.
- Use relative imports (`from ..lib import pdf_document`).
- Don't change `lib/` behaviour just to fit one renamer. If a helper would be useful
  to several renamers, add it to `lib/utils.py` (or `PageTextBoxes`).

## Privacy

Sample PDFs are real bills and bank statements. **Never commit sample PDFs, text dumps,
or real names, addresses or account numbers** (no fixtures, no comments, no test data).
Identification strings in the code should be the issuer's own text (company names,
headings, legal footers), never the customer's details. Keep dumps in a scratch
directory outside the repository.
