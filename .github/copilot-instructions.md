<!--
SPDX-FileCopyrightText: 2025 Nobody (Generated)

SPDX-License-Identifier: 0BSD
-->

## Quick orientation for AI code edits

This repository implements a CLI tool to guess and apply better filenames to PDF bills/statements.
Keep instructions short and code-focused; follow the conventions below when adding or modifying renamers or core behavior.

### Big picture
- CLI entrypoint: `pdfrename.pdfrename:main` (console script `pdfrename`). Use the CLI to run quick checks or apply renames.
- Core pieces:
  - `pdfrename/lib/pdf_document.py` — Document abstraction. `Document(filename)[1]` yields a `PageTextBoxes` object for the first page.
  - `pdfrename/lib/renamer.py` — Renamer registry and `@pdfrenamer` decorator. Renamers return a `NameComponents` object (see below).
  - `pdfrename/renamers/` — Individual service-specific detectors. Files here export functions decorated with `@pdfrenamer`.
  - `pdfrename/lib/utils.py` — helper utilities (normalisation, fake-table parsing, log filters).

### Renamer contract (exact, important)
- A renamer must return either `None` or a `NameComponents` instance from `pdfrename.lib.renamer`.
  - Signature: `def foo(document: pdf_document.Document) -> NameComponents | None` — you get the `Document`.
- Use `@pdfrenamer` to register. The registry is used by `try_all_renamers()`.
- `NameComponents` fields matter for filename generation: `date` (datetime), `service_name` (str),
  `account_holder` (str or sequence), `document_type` (str), optional `account_number` and `document_number`.
- Filenames are produced by `NameComponents.render_filename()` which:
  - starts with `YYYY-MM-DD`, uses ` - ` separators and adds `.pdf`
  - rejects reserved/path characters (raises `InvalidFilenameError`) — ensure values are filename-safe.

### How renamers typically inspect documents
- `Document[1]` returns `PageTextBoxes` which behaves like a list of text boxes. Helpful APIs:
  - `.find_box_starting_with(prefix)` / `.find_index_starting_with(prefix)`
  - `.find_all_matching_regex(pattern)` / `.find_all_indexes_matching_regex(pattern)`
- Utilities to reuse: `build_dict_from_fake_table(fields_box, values_box)`, `extract_account_holder_from_address()`,
  and `utils.normalize_account_holder_name()` for canonical owner names.
- Example pattern: check for a unique company identifier string in `first_page` and parse nearby boxes (see `pdfrename/renamers/aaisp.py` for a concrete example).

### Adding a new renamer (concrete steps)
1. Create a new module in `pdfrename/renamers/`, name it after the service (snake_case).
2. Implement a function with signature V2 (takes `Document`) and decorate with `@pdfrenamer`.
3. Import `NameComponents` and return it when you can confidently match; otherwise return `None`.
4. Use `utils.build_dict_from_fake_table()` for the common two-column fake table pattern.
5. Run `python -m venv venv && . venv/bin/activate && pip install -e .` then test with `pdfrename <file.pdf>` and `--rename`.

### Running & debugging
- Setup: Python 3.12 or later is required.
- Install editable for local iteration:

```bash
python -m venv venv
. venv/bin/activate
pip install -e .[dev]
```

- Common CLI uses (from repo README):
  - Dry-run: `pdfrename unsorted.pdf` (prints suggested renames)
  - Apply: `pdfrename --rename unsorted.pdf`
  - Verbose logging: pass `-v`/`-vv` (click-log configured)
- For noisy pdfminer logs, call `apply_pdfminer_log_filters()` (already done by `main`).
- When a renamer raises, `renamer.py` logs the exception and continues — check tool logs for stack traces.

### Conventions & cautions
- Be conservative: return `None` unless the match is unambiguous. The CLI treats multiple matches as an error (`MultipleRenamersError`).

### Key files to inspect when changing behavior
- `pdfrename/pdfrename.py` — CLI and flow control (`find_filename`, `main`).
- `pdfrename/lib/pdf_document.py` — PDF parsing, extraction, `PageTextBoxes` API.
- `pdfrename/lib/renamer.py` — renamer registry, `@pdfrenamer`, `NameComponents`.
- `pdfrename/lib/utils.py` — normalization and helpers.
- `pdfrename/renamers/*` — real examples of detection/parse patterns.
- `setup.cfg` / `pyproject.toml` — packaging, dependencies, and linting config.

If any section is ambiguous or you want examples for a specific vendor, tell me which file or renamer and I'll extend the guidance or add a small template renamer.
