# PHASE PLAN

Every phase has: **Goal · May touch · Deliverables · Exit criteria (all required) · Owner test · Stop.**
`python scripts/gate_check.py` decides which phase you may work on. A phase is complete only when every exit box is evidenced in its report.

Standing exit criteria for **every** phase: `ruff check` clean · `pytest` green · report written from the template · no real data anywhere · decisions/questions logged · no work from other phases.

---

## PHASE 0 — Notebook audit and technical discovery (documentation only)

**Goal:** Understand the notebook completely, from executable code, before any application is designed.

**May touch:** `docs/**`, `scripts/audit/**` (read-only analysis helpers such as cell extraction). **No application code.**

**Deliverables**
- `docs/NOTEBOOK_ANALYSIS.md`: all 89 cells (58 code): purpose, inputs, outputs, dependencies, duplication group; data-flow diagram (Mermaid); side-by-side diff of cells 75/77/80/82.
- `docs/INDICATOR_DICTIONARY.md`: one entry per output column, using the schema in Master Brief §8.
- `docs/POPULATION_RULES.md`: matrix of population × indicator × pathway × export block, extracted from code (including the commented-out cohort loaders).
- `docs/EXCEL_OUTPUT_SPECIFICATION.md`: blocks, sub-headers, colours, fonts, merges, widths, formulas, per population and period mode, as structured data.
- `docs/KNOWN_ISSUES.md`: every lead L-01…L-17 marked VERIFIED / REFUTED / PARTIAL with cell reference and ≤ 3-line code evidence, plus new findings, severity, and impact.
- `docs/ARCHITECTURE.md` and `docs/IMPLEMENTATION_PLAN.md` (Phase 1 in detail).
- Updated `docs/OPEN_QUESTIONS.md`.

**Exit criteria**
- [ ] Every code cell has an entry in NOTEBOOK_ANALYSIS (count matches 58).
- [ ] Every column produced by any `.agg(...)` or export block appears in the dictionary with all fields filled, or marked UNKNOWN with an open-question ID.
- [ ] Semester logic documented indicator by indicator in one table.
- [ ] Each lead has a verdict with evidence; no lead left unexamined.
- [ ] The four exporters are diffed and a single-parametrised-exporter proposal is written.
- [ ] Indicator names are identical across all documents (checked by a script in `scripts/audit/`).
- [ ] No `.py` application code outside `scripts/audit/`.

**Owner test:** pick ~10 indicators at random and check the dictionary against your own reporting definitions; compare the Excel spec with a real report; rule on every open question tagged "blocks Phase 1/2"; judge the lead verdicts.

**Stop** after `/phase-report`.

---

## PHASE 1 — Foundation, configuration, synthetic data, oracle v0

**Goal:** A solid skeleton, validated configuration, trustworthy fake data, and a runnable copy of the notebook logic to test against.

**May touch:** everything except `reference/` and `docs/gates/`.

**Deliverables**
- Repository skeleton per Master Brief §7; `requirements.txt` (exact pins, verified to install together), `requirements-dev.txt`, `pyproject.toml` (ruff, pytest).
- Typed config models; the five population YAMLs; indicator, period, vocabulary and Excel-template YAML skeletons containing **only confirmed content**; anything unconfirmed is `status: unconfirmed` with the open-question ID. BR-001 is expressed here.
- Identifier-scrubbing logger; exception hierarchy.
- `tests/synthetic/generator.py` per Master Brief §13.1 with `ground_truth.json`.
- `oracle/`: bug-compatible transcription of the notebook logic as callable functions (no Jupyter, no paths).
- `.streamlit/config.toml`; `scripts/` tooling.

**Exit criteria**
- [ ] All five YAMLs load and validate; ≥ 10 negative tests prove invalid config fails with file + key in the message.
- [ ] Logger test: 100 planted UIC strings never appear in captured logs or exception text.
- [ ] Generator is deterministic (same seed → same SHA-256 of output) and plants every defect type in Master Brief §13.1, each with ground truth.
- [ ] Oracle runs end-to-end on synthetic FSW **and** PWID workbooks and emits Q1/Q2/SEM summary frames without error (this proves the generator matches the notebook's structural assumptions).
- [ ] `gate_check.py` has tests.
- [ ] No analytics beyond the oracle.

**Owner test:** run `python scripts/gate_check.py`, `pytest -q`, and the generator for FSW; open the workbook in Excel: sheet names, two header rows, column naming: does it look like your register? Read the FSW and PWID YAMLs: do they say what you intend (NSP difference)?

**Stop.**

---

## PHASE 2 — Ingestion and cleaning

**Goal:** Reliable, auditable ingestion and cleaning with no silent changes.

**May touch:** `core/`, `utils/`, `config/`, `tests/`, `docs/`, `scripts/`.

**Deliverables**
- Ingestion for XLSX/XLS/XLSB (calamine), sheet detection by alias, header-row detection (default `skiprows=2`, configurable), identifier columns read as text.
- Workbook inspector and schema mapper (alias resolution; ambiguity = hard error listing candidates; missing required = structured error); schema compatibility report.
- Cleaning operations with audit trail; vocabulary normalisation replacing `.capitalize()`: unknown values are **reported, not coerced**.
- Duplicate detection (report only), missing-value report.
- CLI: `python -m core.pipeline inspect <file>` (structure-only, safe for real files).
- Performance baseline on a synthetic 80,000 × 300+ workbook; budgets recorded in `docs/DECISION_LOG.md`.

**Exit criteria**
- [ ] The same synthetic content as XLSX, XLS and XLSB yields identical frames.
- [ ] Leading zeros and long numeric IDs preserved (tests).
- [ ] Ambiguous alias raises a named error listing candidate columns; no data in the message.
- [ ] Renamed column resolved via alias; missing required column produces a structured error.
- [ ] Audit trail reconciles: rows in = rows out + rows explicitly dropped (zero unless Owner-approved).
- [ ] Input frame unchanged by cleaning (hash before/after).
- [ ] Every case variant of "Known Positive" is recognised; unknown values are reported, not coerced.
- [ ] Measured time and peak memory reported for 80k × 300; budgets recorded.
- [ ] `inspect` prints no cell values (test asserts output contains no planted values).

**Owner test:** run `inspect` on your real FSW/MSM/TG/PWID/VP workbooks on your own machine (outside the workspace). Confirm sheet detection, header rows and alias resolution are right. Send back the structure-only output if anything is wrong.

**Stop.**

---

## PHASE 3 — Data-quality engine

**Goal:** Every notebook check as a tested, classified rule.

**May touch:** `core/validation.py`, `core/deduplication.py`, `config/`, `tests/`, `docs/`.

**Deliverables**
- Rule registry; each rule has ID, severity, population applicability, description, suggested action.
- Rules per Master Brief §9-D; HIV×ART split per the Owner's answer to OQ-07; CCC check in both directions.
- Result objects, exception DataFrame (rule ID, severity, UIC, region, SR, county, offending column *names*), audit log, `block_on_critical` setting.
- `run --aggregate-only` CLI (counts per rule per SR/county/region; no identifiers).

**Exit criteria**
- [ ] ≥ 3 tests per rule: positive, negative, multi-row-per-UIC edge.
- [ ] On synthetic data, each rule matches `ground_truth.json` exactly (precision and recall 100 %).
- [ ] In legacy mode, flags equal the oracle's (diff table in report).
- [ ] No record is auto-resolved or removed.
- [ ] Runtime on 80k rows measured and within the Phase 2 budget.
- [ ] `--aggregate-only` output contains no identifiers (test).

**Owner test:** run `run --aggregate-only` on real files locally; compare per-rule counts with what your notebook flags for the same rules; explain differences.

**Stop.**

---

## PHASE 4 — Analytical engine

**Goal:** All indicators implemented, first matching the notebook, then corrected one decision at a time.

**May touch:** `analytics/`, `core/periods.py`, `core/compat.py`, `config/`, `tests/`, `docs/`.

**Deliverables**
- Indicator modules per Master Brief §9-E; period engine with explicit mapping and pre-calculation validation; Defined Package driven by YAML (both pathways); KPLHIV and viral load; demographics.
- Compat switches (`config/compat.yaml`).
- `docs/reports/PHASE_4_DIFFERENTIAL.md`: per switch, difference counts on synthetic data and classification.

**Exit criteria**
- [ ] **Stage A:** with all compat switches on, every summary column equals the oracle exactly on synthetic data for all five populations × Q1/Q2/SEM (sole exception: D-001 NSP, documented).
- [ ] **Stage B:** every compat switch flipped off is its own commit, decision-log entry and test.
- [ ] Defined Package matrix tests complete (Master Brief §13.6).
- [ ] Property tests pass (client-grain ≤ `TotalCohort`; Q1 ⊆ SEM; age groups + Unknown = cohort; order invariance).
- [ ] Viral-load parsing tests cover `<200`, `>200`, `LDL`, `>LDL`, `<LDL`, commas, `cp/ml` strings, blanks, junk.
- [ ] Period-mapping validation errors tested (wrong count, wrong identity).
- [ ] Coverage ≥ 90 % on `core/` and `analytics/` (raw output attached).
- [ ] Full 80k × 300 run within budget.
- [ ] Every PROVISIONAL indicator listed with its open-question ID.

**Owner test:** read the differential report and rule on each difference; run `run --aggregate-only` with legacy switches on real data locally and compare SR-by-SR with your notebook; then with corrections on and review the deltas.

**Stop.**

---

## PHASE 5 — Summary and Excel reporting

**Goal:** Reports indistinguishable from today's, produced by one exporter.

**May touch:** `reporting/`, `config/reporting/`, `templates/`, `scripts/`, `tests/`, `docs/`.

**Deliverables**
- Summary builder (explicit group keys; `(MISSING)` geography rows; Unknown sex/age); one parametrised exporter replacing cells 75/77/80/82; template manager driven by `excel_templates.yaml`.
- Run Metadata and Cleaning Log sheets; DQA workbook; cleaned-data workbook (with optional identifier masking); detailed indicator workbook; ZIP package.
- Workbook validator (reopen, structure checks, formulas present, totals cross-checked against pandas; LibreOffice recalculation check if available).
- `scripts/compare_summaries.py`: compares two summary workbooks cell by cell and prints aggregate-only deltas.

**Exit criteria**
- [ ] For each population × period mode, structure matches `EXCEL_OUTPUT_SPECIFICATION.md` (headers, merges, colours, fonts, widths, freeze panes, gridlines, total formulas).
- [ ] New exporter output equals the oracle exporter's output on the same synthetic frame, cell by cell (values and styles); differences documented.
- [ ] PWID has the NSP block; FSW/MSM/TG/VP do not.
- [ ] All five files reopen; ZIP contents verified.
- [ ] Formula totals equal independently computed totals.
- [ ] PROVISIONAL indicators visibly marked in headers and Run Metadata.
- [ ] No group-by silently drops records (test with missing geography).

**Owner test:** generate a package from synthetic data and open every file in Excel next to your real template; then run the engine on your real workbook locally and use `compare_summaries.py` against the workbook your notebook produced; classify every delta.

**Stop.**

---

## PHASE 6 — Streamlit interface

**Goal:** A polished UI that only presents; all logic stays in the engine.

**May touch:** `app.py`, `ui/`, `.streamlit/`, `tests/`, `docs/`.

**Deliverables:** pages per Master Brief §11; session-state machine; progress with per-stage timings; cached runs keyed by file and config hash; friendly data-free errors; download buttons; dashboard from run metadata; read-only Configuration page; identifier-warning and masking option.

**Exit criteria**
- [ ] `streamlit.testing.v1.AppTest` tests for every page.
- [ ] A test fails the build if `ui/` contains indicator logic (e.g., `groupby`/`agg` on analytics frames).
- [ ] Every dashboard number traces to run metadata (test).
- [ ] Upload → Process → Download completes on synthetic 80k × 300 (time and memory reported).
- [ ] Sabotage uploads each show a friendly, data-free message: wrong file type, missing sheet, ambiguous mapping, Critical DQA block, corrupt workbook.
- [ ] Binds to 127.0.0.1; usage stats off.
- [ ] Temp files removed after success and after failure.
- [ ] Screenshots of every page attached to the report.

**Owner test:** use it as a colleague would; try five ways to break it; check every page.

**Stop.**

---

## PHASE 7 — End-to-end validation, hardening, Windows deployment

**Goal:** Prove it, harden it, ship it.

**May touch:** everything except `reference/` and `docs/gates/`.

**Deliverables:** integration tests (5 populations × 3 period modes); large-file performance report; security review checklist (no identifiers in logs, no outbound network calls, `pip-audit`); error-handling review; `README.md`, Windows setup guide, `run_dataflow.ps1`, troubleshooting guide, one-page user guide, CHANGELOG, final implementation report.

**Exit criteria**
- [ ] All earlier phases' tests still green from a clean checkout.
- [ ] Fresh virtual environment built by following the README exactly; `.\run_dataflow.ps1` launches the app (ExecutionPolicy note included).
- [ ] `pip-audit` clean or each finding documented.
- [ ] Network-call test shows no outbound connections during a full run.
- [ ] Final report lists every PROVISIONAL indicator and every unresolved question.

**Owner test (UAT, on real data, outside the workspace):** per population: run, compare with the notebook (all deltas explained), record time taken. Ask a colleague to install from the README alone. Sign-off table in the final report.

**Stop.** Project ends only when the Owner marks Phase 7 APPROVED.
