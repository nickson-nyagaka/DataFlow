# DATAFLOW — Changelog & Transformation Audit

All notable changes and architectural evolutions from the legacy Jupyter notebook (`reference/OPTIMIZED_DATA_MGT.sanitized.ipynb`) to the production-ready **DATAFLOW v1.0.0** desktop application are documented in this file.

The project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-11 — Phase 7 Release (Production Hardening & Windows Deployment)

### Added
- **Automated Windows Dual-Launchers:**
  - `run_dataflow.bat`: Windows Command Prompt / Explorer double-click launcher executing PowerShell with safe session-scoped bypass (`-ExecutionPolicy Bypass -NoProfile`).
  - `run_dataflow.ps1`: Native PowerShell automation script verifying Python 3.11+, creating and activating `.venv`, upgrading `pip`, installing `requirements.txt`, ensuring directory trees, and auto-opening the local browser to `http://127.0.0.1:8501`.
- **Progressive Stress Benchmark Suite (`scripts/audit/benchmark_stress.py`):**
  - Benchmarked scaling matrix: 10,000, 40,000, 80,000, 120,000, and 160,000 rows × 141 columns.
  - Verified 80,000 baseline robustness: executes in **27.3 seconds** with **206.2 MB peak RAM** (budget: < 10 min, < 2.0 GB).
  - Emitted comprehensive performance report in `docs/benchmarks/PERFORMANCE_REPORT.md` (Decision `D-046`).
- **Network Isolation Integration Test (`tests/integration/test_network_isolation.py`):**
  - Socket monkeypatching intercepting `socket.socket.connect` during an end-to-end ingestion, cleaning, DQA, analytics, and reporting run.
  - Proves 0 outbound network calls (Kenya DPA 2019 compliance, Decision `D-047`).
- **Population × Period Matrix Integration Suite (`tests/integration/test_population_period_matrix.py`):**
  - Automated 15-run integration matrix (5 populations × 3 period modes).
  - Validates dynamic formula totals (`diff == 0`), schema conformance (PWID NSP block presence vs non-PWID absence), and ZIP package archive integrity.
- **Data-Free Error Handling Test Suite (`tests/integration/test_error_handling.py`):**
  - Validates graceful rejections for invalid extensions, 0-byte uploads, corrupt archives (`BadZipFile`), missing sheets, and corrupt byte streams without leaking patient data.
- **Sanitized Diagnostic Support Bundle (`core/diagnostics.py`, `ui/about.py`):**
  - One-click ZIP exporter compiling platform environment, config hashes, and redacted execution logs with multi-regex PII scrubbers (`[REDACTED_UIC]`, `[REDACTED_CCC]`, `[REDACTED_NUPI]`, `[REDACTED_PE_CODE]`).
- **Security Vulnerability Audit:**
  - Zero known vulnerabilities verified via `pip-audit -r requirements.txt`.
- **Release Documentation:**
  - Comprehensive `README.md` with Windows quickstart, system requirements, and architecture breakdown.
  - End-user handbook `docs/USER_GUIDE.md` with One-Page Quick Reference Card and Provisional Indicators Appendix (Decision `D-049`).
  - Field troubleshooting manual `docs/TROUBLESHOOTING.md`.
  - Final phase report `docs/reports/PHASE_7_REPORT.md`.

### Optimized
- **Streaming Cleaned Data Exporter (`reporting/cleaned_data_exporter.py`):**
  - Implemented `openpyxl.Workbook(write_only=True)` and streaming row append, reducing memory footprints by > 80% on large cohort exports.
- **Read-Only Ingestion Streaming (`core/ingestion.py`):**
  - Integrated `read_only=True` into pandas `read_excel` openpyxl engine kwargs for sheet preview and loading, eliminating DOM overhead during ingestion.

---

## [0.6.0] - 2026-11-11 — Phase 6 Release (Streamlit Application Interface)

### Added
- **Interactive Multi-Page Streamlit Dashboard (`app.py`, `ui/`):**
  - `ui/dashboard.py`: Summary KPI cards populated strictly from `runtime/run_metadata.json` (zero hardcoded values).
  - `ui/upload.py`: Drag-and-drop file uploader supporting `.xlsx`, `.xlsm`, `.xlsb`, and `.csv` with population and period mode selectors.
  - `ui/processing.py`: Live pipeline progress tracker with per-stage timing chips.
  - `ui/dqa.py`: DQA exception review interface with severity badges and supervisor override modal.
  - `ui/analytics_page.py`: Visual cascade charts for HTS Continuum, PrEP Cascade, and Defined Package retention.
  - `ui/export_page.py`: Download buttons for Master Workbook, Modular Workbooks, and ZIP package, with salted identifier masking toggle (`MASK-XXXX`).
  - `ui/config_page.py`: Read-only configuration viewer displaying effective population rules.
  - `ui/about.py`: System info, compliance badges, and diagnostic bundle generator.
- **Architectural Boundary Enforcement:**
  - Automated test `tests/unit/test_ui.py` fails the build if any indicator formula or dataframe `groupby`/`agg` is detected inside `ui/`.
- **Supervisory Override Console (`core/override.py`):**
  - HMAC-SHA256 supervisor token verification allowing audited exemptions for Critical DQA blocks.

---

## [0.5.0] - 2026-11-10 — Phase 5 Release (Excel Reporting & Packaging Engine)

### Added
- **Declarative Template Manager (`reporting/template_manager.py`):**
  - YAML-driven visual tokens (`config/reporting/excel_templates.yaml`) managing Cascadia Code / Candara typography, row heights, and column widths.
- **Excel Exporters (`reporting/excel_exporter.py`, `reporting/package_builder.py`):**
  - Two-row merged group headers and solid coral (`#FF7D81`) subheaders.
  - Dynamic `=SUM(D3:D<N>)` total row formulas matching national reporting workbooks.
  - Standalone Age × Sex disaggregation pivot sheet (notebook Cell 84).
  - DQA Exceptions exporter with severity color tagging (Peach `#FCE4D6` for Critical, Yellow `#FFF2CC` for Major).
  - Run Metadata and Cleaning Log audit sheets embedded in master workbook.
  - Complete modular ZIP package assembler.
- **Workbook Verification Engine (`reporting/workbook_validator.py`):**
  - Validates sheet existence, freeze panes (`A3`), dynamic formulas, and cross-checks formula sums against pandas ground truth.

---

## [0.4.0] - 2026-11-10 — Phase 4 Release (Vectorised Analytical Engine)

### Added
- **Full Indicator Calculation Pipeline (`analytics/`):**
  - `analytics/prep.py`: PrEP screening, eligibility, new initiations, and refills.
  - `analytics/hts.py`: HIV Testing Services (Tested, Negative, Positive, Linked).
  - `analytics/art.py`: ART status and cohort retention.
  - `analytics/sti.py`: STI screening, diagnosis, and treatment cascades.
  - `analytics/tb.py`: TB screening, presumptive diagnosis, and treatment referral.
  - `analytics/he_rrc.py`: Peer Education and Risk Reduction Counselling indicators.
  - `analytics/condoms.py`: Condom distribution commodity sums.
  - `analytics/nsp.py`: Needle & Syringe Program indicators (active strictly for PWID).
  - `analytics/defined_package.py`: Defined Package Pathways 1 & 2.
  - `analytics/viral_load.py`: Regex extraction and categorization of numeric, LDL, and unparseable viral loads.
  - `analytics/demographics.py`: PEPFAR age group categorization with `(MISSING)` preservation.
- **Dual-Mode Compatibility Layer (`core/compat.py`):**
  - `CompatSwitches` enabling bug-for-bug equivalence with the legacy notebook for verification, with logged diffs when switched off.

---

## [0.3.0] - 2026-11-10 — Phase 3 Release (Demographic & Clinical Cleaning)

### Added
- **Vectorised Demographic Cleaning (`core/cleaning.py`):**
  - Trims leading/trailing whitespace, converts county, region, and Sub-Recipient names to title-case, normalises sex to uppercase `M`/`F`.
- **Date Coercion Pipeline:**
  - Converts mixed date formats (`YYYY-MM-DD`, `DD/MM/YYYY`, Excel serial integers) safely into ISO `YYYY-MM-DD` strings.
- **Clinical Terminology Harmonisation:**
  - Maps messy variations (`"Known Positive"`, `"kp"`, `"positive"`, `"pos"`) to canonical statuses.

---

## [0.2.0] - 2026-11-10 — Phase 2 Release (Ingestion & DQA Validation)

### Added
- **Universal Multi-Format Ingestion (`core/ingestion.py`):**
  - Supports `.xlsx`, `.xlsm`, `.xlsb`, and `.csv` formats.
  - Auto-detects header skiprows (scanning rows 0–15 for anchor tokens).
  - String dtype preservation ensuring leading zeros in UICs, CCCs, and NUPIs are never truncated.
  - Fuzzy column alias resolution with ambiguous mapping rejection.
- **Clinical DQA Rule Engine (`core/validation.py`):**
  - 12 comprehensive rules evaluating clinical integrity, duplicate encounters, and missing demographics.
- **Seeded Synthetic Data Generator (`tests/synthetic/generator.py`):**
  - Generates realistic Register and KPLHIV sheets with planted defects and emits `ground_truth.json` for deterministic testing.

---

## [0.1.0] - 2026-11-10 — Phase 1 Release (Scaffolding & Configuration)

### Added
- **Declarative Configuration Architecture:**
  - Population configs: `config/populations/fsw.yaml`, `msm.yaml`, `pwid.yaml`, `tg.yaml`, `vp.yaml`.
  - Reporting period mappings: `config/periods.yaml`.
- **Deterministic Gate Check System (`scripts/gate_check.py`):**
  - Strict Phase Gate enforcement verifying Owner approval before allowing progression to subsequent phases.

---

## [0.0.0] - 2026-11-10 — Phase 0 Release (Legacy Notebook Forensic Audit)

### Added
- **Forensic Notebook Analysis (`reference/OPTIMIZED_DATA_MGT.sanitized.ipynb`):**
  - Analyzed all 104 notebook cells.
  - Extracted golden cell execution outputs, visual palettes, and table structures.
  - Documented 10 critical legacy anomalies (L-01 through L-10) in `docs/KNOWN_ISSUES.md`.
