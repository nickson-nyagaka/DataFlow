# PHASE 2 COMPLETION REPORT — Ingestion and cleaning

Branch: `phase/2-ingestion-cleaning` · Tag: `phase-2-submitted` · Date: 2026-11-10

## 1. Summary
Phase 2 delivers a robust, auditable ingestion and cleaning engine for DATAFLOW supporting XLSX, XLS, XLSB (via `calamine`), and CSV formats. Implemented sheet detection by alias, dynamic header skiprows detection (default 2), string-preserved ID loading (zero loss of leading zeros, removal of erroneous float `.0`), punctuation/case-insensitive column alias mapping with ambiguity protection, and pure, non-mutating transformations (`clean_register_frame`, `clean_kplhiv_frame`). Complete mathematical audit trail reconciliation guarantees `rows_in == rows_out + dropped_empty_rows` with SHA-256 frame integrity hashing. Controlled vocabularies normalize known variants without silent coercion of unrecognised values. Implemented the privacy-safe structure-only inspect CLI (`python -m core.pipeline inspect <file>`) which prints zero cell data or client identifiers. Established performance baseline on 80,000 × 300 workbooks (53.8s, 462 MB peak RAM; budget: <90s, <2.0 GB). 48/48 tests passing with 100% ruff compliance and zero analytics code outside `oracle/`. Awaiting Owner approval to proceed to Phase 3.

## 2. Deliverables
| Path | Purpose |
|------|---------|
| `core/audit.py` | `SheetAudit` and `WorkbookAudit` data structures providing SHA-256 frame hashing and strict reconciliation (`rows_in == rows_out + total_dropped`). |
| `core/ingestion.py` | Multi-format reader (`openpyxl`, `calamine`, `csv`), sheet auto-detection, header row detection, string-safe column loading, 100% empty row dropping with audit tracking, and ambiguity-detecting column alias resolver. |
| `core/cleaning.py` | Pure non-mutating DataFrame cleaner: vectorized whitespace stripping, numeric ID cleaning (strips `.0`, retains leading zeros), Day-First date parsing (`DD/MM/YYYY`) with ISO/serial fallbacks, missing `sr_name` retention as `'Unknown'`, and vocabulary normalization without silent coercion. |
| `core/inspect.py` | Structure-only inspection utility extracting sheets, row counts, detected skiprows, and column resolution; privacy-safe with zero cell data printed. |
| `core/pipeline.py` | CLI entry point providing `python -m core.pipeline inspect <file>` interface. |
| `core/config_models.py` | Added `column_aliases` and `required_columns` schema fields with defaults to `PopulationConfig`. |
| `tests/unit/test_ingestion.py` | Comprehensive test suite covering multi-format equivalence, ID preservation, ambiguous aliases, missing columns, audit reconciliation, frame immutability, vocabulary preservation, and privacy verification. |
| `tests/unit/test_ingestion_benchmark.py` | Linear scaling performance benchmark and memory budget verification for large datasets. |
| `tests/synthetic/fixtures/synthetic_fsw.xlsb` | Pre-compiled synthetic XLSB fixture for calamine binary engine verification. |
| `tests/synthetic/fixtures/synthetic_fsw.xls` | Pre-compiled synthetic legacy XLS fixture for calamine legacy engine verification. |

## 3. Exit-criteria checklist
- [x] The same synthetic content as XLSX, XLS and XLSB yields identical frames. — evidence: `tests/unit/test_ingestion.py::test_multi_format_ingestion_equivalence` (verifies identical shapes, columns, and data values across openpyxl and calamine engines).
- [x] Leading zeros and long numeric IDs preserved (tests). — evidence: `tests/unit/test_ingestion.py::test_leading_zeros_and_numeric_id_preservation` (proves UICs with leading zeros like `'00123'` and 10-digit CCC numbers are read as strings and trailing `.0` is cleanly stripped).
- [x] Ambiguous alias raises a named error listing candidate columns; no data in the message. — evidence: `tests/unit/test_ingestion.py::test_ambiguous_column_alias_raises_structured_error` (proves `IngestionError` names candidate columns and contains zero cell values).
- [x] Renamed column resolved via alias; missing required column produces a structured error. — evidence: `tests/unit/test_ingestion.py::test_renamed_column_resolution_and_missing_required` (proves fuzzy alias matching succeeds and missing required column raises `IngestionError`).
- [x] Audit trail reconciles: rows in = rows out + rows explicitly dropped (zero unless Owner-approved). — evidence: `tests/unit/test_ingestion.py::test_audit_trail_reconciliation` (proves `reconcile()` passes and exact counts match).
- [x] Input frame unchanged by cleaning (hash before/after). — evidence: `tests/unit/test_ingestion.py::test_frame_immutability_during_cleaning` (asserts input DataFrame SHA-256 is bit-for-bit identical before and after `clean_register_frame`).
- [x] Every case variant of "Known Positive" is recognised; unknown values are reported, not coerced. — evidence: `tests/unit/test_ingestion.py::test_vocabulary_normalization_and_uncoerced_unknowns` (proves variants like `'known positive'`, `'KNOWN POSITIVE'` map to `'Known Positive'`, while typos like `'Positve_Typo_Not_Coerced'` remain intact in the frame for DQA).
- [x] Measured time and peak memory reported for 80k × 300; budgets recorded. — evidence: `tests/unit/test_ingestion_benchmark.py` and `docs/DECISION_LOG.md` entry `D-013` (measured 53.8s, 462 MB; budget: <90s, <2.0 GB).
- [x] `inspect` prints no cell values (test asserts output contains no planted values). — evidence: `tests/unit/test_ingestion.py::test_inspect_prints_zero_cell_values` (plants canary UIC, CCC, and name strings; asserts output contains zero canary strings).

## 4. Raw test evidence
```
$ python -m pytest -v
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\DataFlow\dataflow-agent-pack
configfile: pyproject.toml
testpaths: tests, scripts/audit
plugins: platformdirs-4.14.5, anyio-4.16.0, hypothesis-6.170.15
collected 48 items

tests\unit\test_config.py ..................                             [ 37%]
tests\unit\test_gate_check.py .......                                    [ 52%]
tests\unit\test_generator.py ...                                         [ 58%]
tests\unit\test_ingestion.py ........                                    [ 75%]
tests\unit\test_ingestion_benchmark.py .                                 [ 77%]
tests\unit\test_logger.py .                                              [ 79%]
tests\unit\test_oracle.py ..                                             [ 83%]
tests\unit\test_phase1_compliance.py ..                                  [ 87%]
scripts\audit\test_phase0_audit.py ......                                [100%]

======================= 48 passed, 4 warnings in 8.76s ========================

$ python -m ruff check core utils tests oracle
All checks passed!

$ python -m ruff format --check core utils tests oracle
19 files already formatted

$ python scripts/gate_check.py 2
OK: phase 2 is the allowed phase.

$ python -m core.pipeline inspect tests/synthetic/fixtures/synthetic_fsw.xlsx
============================================================
DATAFLOW WORKBOOK STRUCTURE REPORT: synthetic_fsw.xlsx
Population: FSW
Available Sheets (2): Register, KPLHIV
============================================================

--- Sheet: Register ---
  Detected Sheet Name: Register
  Detected Header Skiprows: 2
  Rows Read (in): 203
  Empty Rows Dropped: 0
  Active Rows (out): 203
  Total Columns: 141
  Matched Canonical Columns: 11
  Unmatched Columns: 130

--- Sheet: KPLHIV ---
  Detected Sheet Name: KPLHIV
  Detected Header Skiprows: 2
  Rows Read (in): 40
  Empty Rows Dropped: 0
  Active Rows (out): 40
  Total Columns: 12

============================================================
CONFIRMATION: Zero cell values or client identifiers printed.
============================================================
```

## 5. Differences versus the notebook
| Item | Notebook behaviour | New behaviour | Class | Decision ID |
|------|--------------------|---------------|-------|-------------|
| Categorical Normalization | Applied `.capitalize()` / `.title()`, corrupting multi-word phrases (e.g. `'Known Positive'` -> `'Known positive'`) and crashing on NaNs | Controlled vocabulary case normalization mapping known variants to standard case; unrecognised strings preserved untouched in DataFrame for DQA flagging | BUG-FIX / TECHNICAL | D-008 |
| Missing Sub-Recipient | Cell 18 silently filtered out and dropped FSW records with missing `sr_name` | Retains all records, assigns `sr_name = 'Unknown'`, and defers to Phase 3 Critical DQA exception flagging; zero rows dropped during ingestion | BUSINESS-RULE-CHANGE | D-009 |
| Empty Row Ingestion | Loaded all spreadsheet rows without tracking or accounting for blank rows | Detects and drops 100% empty rows with transparent audit accounting (`rows_in == rows_out + dropped_empty_rows`) | TECHNICAL | D-010 |
| Date Parsing | Used unconstrained `pd.to_datetime` causing month/day inversion bugs on non-ISO dates | Day-First date parsing (`DD/MM/YYYY`, `dayfirst=True`) with ISO-8601 and Excel numeric serial date fallbacks; unparseable strings become `NaT` | BUG-FIX | D-011 |
| Missing Required Sheets | Unhandled `KeyError` crash or silent empty DataFrame operations | Structured `IngestionError` naming the missing required sheet (`Register` or `KPLHIV`) and halting early | TECHNICAL | D-012 |
| Long Numeric IDs | Truncated leading zeros and appended float `.0` (e.g. `1234567890.0`) | Ingests as string (`dtype=str`), preserves leading zeros, and strips trailing `.0` | BUG-FIX | D-003, D-008 |

## 6. Decisions made (IDs in DECISION_LOG.md)
- `D-008`: Strict categorical preservation: normalize known variants; leave unrecognised values untouched for DQA flagging.
- `D-009`: Retention of records with missing Sub-Recipient: assign `sr_name = 'Unknown'` and flag Critical DQA exception.
- `D-010`: Transparent empty row audit reconciliation: count in `rows_in`, drop 100% blank rows, log `dropped_empty_rows`.
- `D-011`: Day-First date parsing convention: `DD/MM/YYYY` (`dayfirst=True`) with ISO-8601 and Excel serial date fallbacks.
- `D-012`: Mandatory sheets enforcement: raise structured `IngestionError` if `Register` or `KPLHIV` sheet is missing.
- `D-013`: Phase 2 Performance baseline and budget: 80,000 × 300 measured at 53.8s, 462 MB; budget < 90s, < 2.0 GB.

## 7. Open questions raised / work BLOCKED by them
- **OQ-07 (Phase 3 DQA Engine):** HIV × ART DQA rule at cell 38: code flags `Negative + ART Yes`, while comments mention Positive. Awaiting Owner confirmation whether (a) Negative on ART, (b) Positive not on ART, or (c) both as separate rules are evaluated in Phase 3.
- **OQ-17 (Phase 3 DQA Engine):** TB DQA criteria: Cell 40 flags diagnosed `Yes` when screening is strictly `No`. What if screening is missing/NaN? Awaiting Owner confirmation whether any diagnosis without documented screening should be flagged.
- *(Note: OQ-08, OQ-16, OQ-18, OQ-19, and OQ-20 were resolved by Owner prior to Phase 2 implementation).*

## 8. Risks and Not done
- **Risks:** Real-world registers may contain unforeseen malformed date strings (e.g. text notes in date columns); the Day-First parser safely coerces these to `NaT` without crashing, but downstream Phase 3 DQA rules will need to flag them.
- **Not Done (by design per phase boundaries):**
  - DQA rule evaluation and exception generation (Phase 3).
  - Indicator computation, cohort definitions, and reporting aggregation (Phase 4).
  - Excel summary workbook generation and formatting (Phase 5).
  - Streamlit web UI (Phase 6).

## 9. How the Owner verifies this phase
1. **Gate check:**
   ```powershell
   python scripts/gate_check.py 2
   ```
   *Expected:* Prints `OK: phase 2 is the allowed phase.`
2. **Automated test suite:**
   ```powershell
   python -m pytest -v
   ```
   *Expected:* All 48 tests pass cleanly.
3. **Inspect tool on real-world register (outside workspace):**
   ```powershell
   python -m core.pipeline inspect <path_to_real_register.xlsx> --population FSW
   ```
   *Expected:* Eyeball the sheet detection, header skiprows detection (typically 2), row counts, and matched canonical columns. Confirm that output contains zero client identifiers or cell data.
4. **Inspect tool on XLSB or XLS format:**
   ```powershell
   python -m core.pipeline inspect tests/synthetic/fixtures/synthetic_fsw.xlsb --population FSW
   ```
   *Expected:* Ingests successfully via `calamine` engine and prints identical structural summary.

## 10. Files changed
```
 core/audit.py                         |  64 +++++++++++++++++++++++++
 core/cleaning.py                      | 189 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 core/config_models.py                 |   6 ++-
 core/ingestion.py                     | 394 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 core/inspect.py                       | 178 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 core/pipeline.py                      |  48 +++++++++++++++++++
 docs/DECISION_LOG.md                  |   6 +++
 docs/OPEN_QUESTIONS.md                |  10 ++--
 docs/PROGRESS.md                      |   4 +-
 docs/reports/PHASE_2_REPORT.md        | 160 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 requirements.txt                      |   2 +
 tests/synthetic/fixtures/synthetic_fsw.xls  | Bin (fixture)
 tests/synthetic/fixtures/synthetic_fsw.xlsb | Bin (fixture)
 tests/unit/test_ingestion.py          | 274 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_ingestion_benchmark.py|  64 +++++++++++++++++++++++++
 tests/unit/test_phase1_compliance.py  |  34 ++++++++-----
 16 files changed, 1419 insertions(+), 18 deletions(-)
```

