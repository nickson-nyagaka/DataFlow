# DATAFLOW — Master Brief (v2)

**Automated Key Population Data Management, Cleaning, Analytics and Excel Reporting**

Owner: Nickson Nyagaka (senior M&E / BI data analyst). Reader: an autonomous engineering agent.
Authority: this brief and `AGENTS.md`. The notebook is evidence, not specification.

---

## 1. Mission

Turn the legacy Jupyter notebook into a tested, configurable local application. The normal workflow must be:

**UPLOAD → INSPECT → CLEAN → VALIDATE → ANALYZE → SUMMARIZE → EXPORT**

A non-programmer drops in one consolidated workbook (sheets `Register` and `KPLHIV`), picks the population and reporting period, clicks Process, and receives a complete reporting package: a summary workbook matching the existing template, a data-quality exceptions workbook, a cleaned-data workbook, a detailed indicator workbook, a run-metadata sheet, and a ZIP of everything.

The goal is **not** to recreate a notebook inside Streamlit. It is to extract the analytical knowledge, engineer it into a tested engine, and wrap a reliable application around it.

### Success looks like
- Numbers match the notebook wherever the notebook was right, and every deviation is classified and Owner-approved.
- Every number in a report can be traced to a rule, a config entry and an input file hash.
- A colleague installs it from the README alone and produces a package without help.
- 80,000 rows × 300+ columns processes in minutes, not hours (budget set in Phase 2, enforced from then on).

## 2. Scope

**In:** FSW, MSM, PWID, TG, VP; XLSX/XLS/XLSB ingestion; schema mapping; cleaning with audit trail; DQA engine; all indicators in the notebook; Q1/Q2/Semester; summaries by county/SR/region/age/sex; Excel reporting; Streamlit UI; pytest suite; Windows launch script.

**Out (this release):** databases, cloud, authentication, multi-user, FastAPI/Django, auto-correction of source data, any external AI processing of records.

## 3. Reference material and how to treat it

`reference/OPTIMIZED_DATA_MGT.sanitized.ipynb` — 89 cells (58 code), outputs cleared. Cell numbers below are **0-based** and were verified by a pre-audit.

| Cell | What it contains |
|---|---|
| 17 | Duplicate-UIC check (lists duplicates; does not remove them) |
| 38 | HIV × ART consistency check (code flags **Negative + ART Yes**; surrounding comments talk about positives) |
| 46 | Dataset assignment bug (`ConsolidatedKPLHIV = ConsolidatedFSW.drop(...)`) |
| 54 | Viral-load standardisation and suppression |
| 57 | Age-group assignment (missing age falls into 'Below 15') |
| 61 | All coverage indicators: Q1/Q2/SEM flags, positional column slicing, Defined Package (both pathways), NSP (requirements commented out) |
| 75 | Export: Q1 only, no NSP (sheet `KP_Summary`) |
| 77 | Export: Q1 only, with NSP block (sheet `PWID_Summary`) |
| 80 | Export: Q1/Q2/SEM, no NSP (sheet `Summary`) |
| 82 | Export: Q1/Q2/SEM, with NSP block (sheet `PWID_Summary`) |
| 84 | Age/sex pivot containing `.fillna('F')` |

Cells 75/77/80/82 are four near-copies of one exporter. They must become **one parametrised exporter** with no change to what the user sees.

## 4. Business rules already confirmed by the Owner

| ID | Rule |
|---|---|
| BR-001 | **NSP is a required component of the general Defined Package pathway for PWID only.** FSW/MSM/TG/VP: not required. Expressed in YAML, never in `if population == ...` code. The alternative **PLHIV-service pathway** is preserved separately; whether NSP applies there is **OQ-01** (do not assume). The notebook comments NSP out of both pathways for all populations, so BR-001 is a deliberate change: tests will show expected differences and they must be classified, not hidden. |
| BR-002 | NSP **receipt** (client-level, >0 distributed in the period) ≠ NSP **quantity** (commodity, sum). Never conflate them. Presence of a quantity does not by itself prove a client met the Defined Package. |
| BR-003 | Viral-load suppressed = `LDL` or numeric `< 200`. Keep until the Owner changes it. |
| BR-004 | Never default missing sex to Female. Missing sex is reported as `Unknown`. |
| BR-005 | Never auto-delete duplicate UICs. Flag them; policy is OQ-04. |
| BR-006 | Age categories are template-specific. Preserve each template's categories until the Owner supplies one standard. Missing age is `Unknown`, never 'Below 15'. |
| BR-007 | Reporting periods are explicit source-column → period mappings in config. No alphabetical or positional inference. |
| BR-008 | Local processing only. Real data never enters the workspace. |

## 5. Pre-audited leads (hypotheses from a reading pass, NOT yet verified by execution)

Phase 0 must verify or refute every one against the code, with evidence, and record outcomes in `docs/KNOWN_ISSUES.md`. Discard those that do not hold. Add anything you find.

| Lead | Where | Why it matters |
|---|---|---|
| L-01 | Cell 46 | KPLHIV overwritten by Register data when column `s_n` exists. |
| L-02 | Cell 38 | Rule vs comment mismatch. Decide the intended DQA rule(s) (OQ-07). |
| L-03 | Cell 17 + 61 + summaries | Duplicates are listed but kept. Flags are propagated to every row of a UIC (`any_in_unique_allrows`) and then **summed per row**, while `TotalCohort` uses `nunique`. Numerators can exceed the cohort. |
| L-04 | Both cleaning cells | Every string cell goes through `.capitalize()`. `Known Positive` becomes `Known positive`, but later code compares against **both** spellings in different places. Replace with an approved vocabulary map (OQ-08). |
| L-05 | Cells 57, 84 | Missing age handled inconsistently; missing age lands in 'Below 15'. |
| L-06 | Cell 84 | `.fillna('F')` on sex. |
| L-07 | Cell 61 and DQA cells | Quarter columns taken positionally (`cols[:3]`, `cols[3:6]`) after plain `sorted()` (lexicographic: `_10` sorts before `_2`) while one check uses `natsorted`. PrEP×HIV and ART×HIV checks pair columns by sorted position (`zip`). |
| L-08 | Cell 54 and KPLHIV summary | `Suppressed` sums **rows**, `Total_KPLHIV` counts **unique clients**. No "latest VL" or time-window logic. Unparseable values become `UNKNOWN` and count as not suppressed. |
| L-09 | Summary cells | `groupby` silently drops rows with missing county/SR/region. Join keys are normalised via `astype(str)` (NaN becomes `'nan'`/`'NAN'`) and flip between `.title()` and `.upper()`; a spelling difference makes a left merge yield NaN with no warning. |
| L-10 | Cell 61 (`hts_sem`) | `enrolled_Apr_plus` uses `month >= 7` while a comment says "Apr … month >= 10". Month only, no year. |
| L-11 | Final summary cell | `OLD_Cohort` / `NEW_Cohort` are referenced in column ordering but never computed (silently filtered out). |
| L-12 | Many | Hardcoded months (`jul…dec`), `skiprows=2`, machine path, Q1/Q2 labels regardless of real calendar. |
| L-13 | Cells 75/77/80/82 | Four near-identical exporters. |
| L-14 | Cleaning cells | `.map(...)` over every cell of an 80k×300 frame; very slow. |
| L-15 | Cell 61 | Semester logic differs by indicator (HTS uses AND/OR, others union; `New_on_ART` uses Q1 columns only). Document indicator by indicator; never assume uniformity. |
| L-16 | CCC check | One direction only (KPLHIV → Register). Null CCC numbers are not counted. |
| L-17 | Cell 61 | NSP requirements commented out of both Defined Package pathways, including the PWID path (see BR-001). |

## 6. Technology stack

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| UI | Streamlit (local only) |
| Data | pandas (≥ 2.2), NumPy |
| Excel in | pandas with `engine="calamine"` (python-calamine) for XLSX/XLS/XLSB; CSV optional later |
| Excel out | openpyxl |
| Config | YAML + typed validation models (Pydantic v2 recommended); Pandera optional for DataFrame schemas |
| Logging | stdlib `logging` with an identifier-scrubbing filter |
| Tests | pytest, pytest-cov, **hypothesis** (property tests) |
| Quality | ruff (lint + format), pre-commit optional, `pip-audit` in Phase 7 |
| Charts | Plotly |
| Packaging | zipfile, `requirements.txt` (exact pins), `run_dataflow.ps1` |

Do not introduce Django, FastAPI, PostgreSQL, Redis or cloud services. Keep `natsort` if natural ordering is ever needed for labelling, but never for period assignment.

## 7. Architecture

```text
DATAFLOW/
├── app.py
├── requirements.txt · requirements-dev.txt · pyproject.toml · README.md
├── .streamlit/config.toml        # 127.0.0.1, usage stats off, upload limit set
├── config/
│   ├── settings.yaml · compat.yaml          # compat = legacy-behaviour switches
│   ├── populations/ fsw|msm|pwid|tg|vp .yaml
│   ├── indicators/  prep|hts|art|sti|tb|condoms|nsp|defined_package .yaml
│   ├── vocabularies/ *.yaml                 # allowed values + canonical forms
│   └── reporting/   periods.yaml · excel_templates.yaml
├── core/        ingestion · workbook_inspector · schema_mapper · cleaning ·
│                deduplication · validation · periods · compat · pipeline · exceptions
├── analytics/   prep · hts · art · sti · tb · condoms · nsp · defined_package ·
│                demographics · kplhiv · viral_load · peer_education · summaries
├── reporting/   excel_exporter · template_manager · summary_builder · dqa_exporter ·
│                cleaned_data_exporter · package_builder · workbook_validator
├── ui/          dashboard · upload · processing · data_quality · analytics · exports · configuration
├── utils/       logger · identifiers · dates · helpers
├── oracle/      frozen, bug-compatible transcription of the notebook logic (TEST-ONLY)
├── tests/       fixtures/ · synthetic/generator.py · unit/ · property/ · differential/ · golden/
├── scripts/     gate_check.py · sanitize_notebook.py · compare_summaries.py · …
├── templates/   FSW MSM PWID TG VP
├── docs/        (see PHASE_PLAN) · reports/ · gates/
└── runtime/     temporary/ · exports/ · logs/     (git-ignored)
```

Separation is mandatory: presentation, processing, analytics, configuration, reporting, testing. The engine runs without Streamlit (CLI: `python -m core.pipeline ...`).

### Two CLI modes that make real-data testing safe
- `inspect <file>`: structure only (sheet names, header row, column names, counts, alias resolution). Never prints cell values.
- `run <file> --aggregate-only`: indicator totals per SR/county/region and DQA counts per rule. Never prints identifiers or row-level data.

The Owner runs these on real files on his own machine, outside the workspace, and reports results back. The agent never sees real rows.

## 8. Indicator dictionary schema (Phase 0 output, one entry per output column)

| Field | Meaning |
|---|---|
| `id` / `output_column` | Stable ID and the exact legacy column name |
| `label` | Human label used in the Excel sub-header |
| `populations` | Where applicable |
| `grain` | `client` / `encounter` / `commodity` |
| `source_columns` | Column family regex **and** explicit period mapping |
| `source_values` | Values counted (after vocabulary normalisation) |
| `period_logic` | Q1, Q2, SEM, each stated separately |
| `propagation` | Whether `any_in_unique_allrows` semantics apply |
| `aggregation` | e.g. `nunique(uic where flag)`, `sum(quantity)` |
| `notebook_ref` | Cell indices |
| `legacy_quirks` | Behaviours the compat layer must reproduce |
| `status` | `CONFIRMED` / `PROVISIONAL` + open question ID |

## 9. Functional modules (condensed; the full detail lives in PHASE_PLAN)

**A. Ingestion** — XLSX/XLS/XLSB; sheet detection by alias; header-row detection (default `skiprows=2`, configurable); identifiers read as text (leading zeros preserved, never floats); workbook inspection report; missing/unexpected/renamed column detection.

**B. Schema mapping** — alias lists per standard field; ambiguity is a hard stop that lists candidates (no fuzzy guessing); schema compatibility report.

**C. Cleaning** — column-name standardisation, trimming, vocabulary normalisation (replaces `.capitalize()`), identifier normalisation, numeric/date parsing, missing-value classification, uppercase geography where the template needs it. Source values preserved; every operation writes an audit entry (rule ID, columns, rows affected).

**D. DQA** — rule registry with ID, severity (Critical/Major/Minor/Info), population applicability, description, suggested action. Rules: duplicate UIC; missing UIC/county/age/DOB/enrolment date/PE code/geography; invalid sex; invalid HIV status; PrEP inconsistencies; HIV×PrEP; HIV×ART (per OQ-07); TB diagnosed without screening; STI diagnosed without screening; CCC/NUPI mismatch (both directions). Nothing is auto-resolved. Critical findings can block final report generation (`block_on_critical`, default true).

**E. Analytics** — PrEP, HTS, ART, STI, TB, condoms, NSP, Defined Package (two pathways), peer education, KPLHIV, viral load, demographics. Q1, Q2 and Semester per indicator, each documented separately. Unavailable source columns follow applicability rules and are reported, not skipped.

**F. Period engine** — explicit column→period maps in `periods.yaml`; pre-calculation validation of the expected count and identity of columns; clear errors.

**G. Summary engine** — by county, SR, region, age group, sex, age×sex, period, population. Missing geography is shown as its own row (`(MISSING)`), never dropped. Client indicators use unique-client counts; commodities sum; peer educators count unique codes.

**H. Excel engine** — see §10.

**Compat layer** — `config/compat.yaml` holds one switch per known legacy behaviour (e.g. `legacy_capitalize_vocabulary`, `legacy_missing_age_below_15`, `legacy_row_sum_flags`). Phase 4 first proves engine == oracle with all switches on, then flips them off one at a time, each with a logged diff and a decision entry.

## 10. Excel specification (preserve; extract exact values in Phase 0)

- openpyxl; two-row merged headers (row 1 group, row 2 sub-header); single-column blocks merged vertically.
- Header font Cascadia Code bold; body font Candara; sub-header fill `FF7D81`; total fill `6BD669`; group colours as in the notebook map; borders; centred headers; freeze panes `A3`; gridlines off; formula-based TOTAL row (`SUM`) merged across the first three columns; widths 22 (first three) / 14 (others); row heights 22/30.
- NSP uses the coral fallback (`FF7D81`) unless a reference template says otherwise (OQ-13).
- PWID reports include the NSP block. Other populations do not.
- Additional sheets: **Run Metadata** (app version, config hash, input SHA-256, population, period, timestamp, PROVISIONAL indicators, compat switch state) and **Cleaning Log**.
- Every exported file must reopen with openpyxl, and structural checks must pass (headers, merges, colours, fonts, formulas, totals cross-checked against pandas).
- Formulas have no cached values until Excel recalculates; the validator must also verify totals independently of the formulas.

## 11. Streamlit specification

Name: **DATAFLOW** — *Automated Data Management & Reporting System*.
Pages: Dashboard · Upload Data · Processing · Data Quality · Analytics · Export Reports · Configuration (read-only in v1: effective config, validation status, diff against defaults) · About.

- Dashboard figures come only from the latest run's metadata (JSON in `runtime/`, no identifiers). No hardcoded statistics.
- Heavy work runs through the engine, cached by input file hash and config hash, with state in `st.session_state`; `st.status` for per-stage progress and timings.
- Errors are friendly and contain no record-level data. Downloads are served from files on disk after the run completes.
- Exports page warns that files may contain UICs and offers "mask identifiers".
- No indicator formula in `ui/`.

## 12. Performance and security

- Target: 80,000+ rows × 300+ columns. Vectorised pandas, `category`/`string` dtypes where sensible, minimal copies. Report time and peak memory per stage. Budgets are fixed in Phase 2 from a measured baseline and enforced after.
- Local only. No telemetry. No identifiers in logs, tracebacks, test names or commit messages. Temp files cleaned on success and failure. `.gitignore` excludes runtime output, real data and workbooks outside fixtures/templates.

## 13. Testing strategy

1. **Synthetic data generator** (seeded, deterministic): produces Register + KPLHIV workbooks for every population, with planted defects (duplicate UICs, mixed-case statuses, float-formatted IDs, missing ages/sex/county, `LDL`/`<LDL`/`>LDL`/`9250cp/ml`/`1,200` viral loads, Negative-on-ART, Positive-without-ART, TB/STI diagnosed-not-screened, PrEP in Positive clients, CCC mismatches, ≥ 10 visit columns to trigger sort traps, NaN geography, renamed columns, extra columns). It also emits a `ground_truth.json` with the planted counts.
2. **Unit tests** for every function and rule (positive, negative, edge, multi-row UIC).
3. **Property tests** (hypothesis): client-grain counts ≤ `TotalCohort`; Q1 ⊆ SEM where defined; age groups + Unknown = cohort; aggregation is invariant to row order; no UIC ever appears in logs.
4. **Differential tests**: oracle (notebook-faithful) vs engine on synthetic data, all populations × periods, exact column-by-column comparison; every difference classified (`BUG-FIX`, `BUSINESS-RULE-CHANGE`, `DEFECT`, `AMBIGUOUS`).
5. **Golden workbook tests**: exporter output vs the oracle exporter's output, cell by cell (values and styles).
6. **Defined Package matrix**: 5 populations × (NSP missing/present) × (each other component missing) × (PLHIV pathway) × (Q1/Q2/SEM) × (multi-row UIC).
7. **Owner UAT on real data** (Phase 7), using the aggregate-only CLI and `scripts/compare_summaries.py`.

## 14. Definition of done (whole project)

All eight phases APPROVED by the Owner; all tests green from a clean checkout; UAT sign-off for all five populations; no PROVISIONAL indicator without a recorded Owner acceptance; README verified on a fresh machine.
