# DATAFLOW — Automated HIV Key Population Cohort Data Management & Reporting System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red.svg)]()
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Privacy: Kenya DPA 2019](https://img.shields.io/badge/privacy-Kenya%20DPA%202019%20Compliant-green.svg)]()

**DATAFLOW** is an automated, privacy-preserving desktop application and high-throughput analytical pipeline designed for Sub-Recipient (SR) and Principal Recipient (PR) M&E teams managing national HIV Key Population programs in Kenya.

DATAFLOW ingests raw, messy cohort workbooks (covering **FSW**, **MSM**, **PWID**, **TG**, and **VP** populations), performs strict schema and data quality assurance (DQA) validation, executes 88 standardized indicator calculations across PrEP, HTS, ART, TB, STI, Condoms, and Defined Package cascades, and exports pixel-perfect, formula-verified Excel reporting workbooks and modular ZIP packages.

---

## Key Capabilities

- **Multi-Population & Multi-Period Coverage:** Full support for Female Sex Workers (FSW), Men who have Sex with Men (MSM), People Who Inject Drugs (PWID), Transgender (TG), and Vulnerable Populations (VP) across Semester (SEM), Quarter 1 (Q1), and Quarter 2 (Q2) reporting intervals.
- **Robust Ingestion Engine:** Resolves header skiprows automatically, maps messy or renamed column aliases, preserves leading zeros in national identifiers (UICs, CCC numbers, NUPIs), and gracefully rejects corrupt archives or invalid schemas without leaking sensitive client data.
- **Automated DQA & Exception Reporting:** Validates 12 clinical and structural rules (e.g., negative-on-ART, positive-without-ART, PrEP in known positives, TB/STI diagnosis without screening, duplicate UIC encounters). Generates dedicated DQA exception workbooks with suggested remediation steps.
- **Supervisory Override System:** Enables authorized M&E supervisors to grant cryptographically audited, time-stamped exemptions for known field anomalies using an HMAC-SHA256 supervisor token.
- **Pixel-Perfect Excel Generation:** Produces multi-tab workbooks identical to national reporting templates, complete with palette styling, dynamic Excel `=SUM()` formulas, disaggregated Age × Sex pivot tables, Run Metadata audit trails, and optional client identifier masking (`MASK-XXXX`).
- **Privacy & Kenya DPA 2019 Compliance:** Strict 100% local offline execution. Intercepts and blocks all outbound network sockets. Zero PII or patient UICs in logs, tracebacks, or diagnostic bundles. Telemetry and cloud analytics are permanently disabled.

---

## System Requirements

- **Operating System:** Windows 10, Windows 11, or Windows Server (x64)
- **Python:** Python 3.11, 3.12, 3.13, or 3.14 (64-bit recommended)
- **Memory (RAM):**
  - Minimum: 4 GB RAM (cohorts up to 40,000 clients)
  - Recommended: 8 GB – 16 GB RAM (cohorts 80,000 – 160,000+ clients)
- **Disk Space:** 500 MB free space for virtual environment and temporary reporting artifacts.
- **Display:** 1280 × 720 minimum screen resolution (optimized for desktop and laptop displays).

---

## One-Click Quickstart on Windows

DATAFLOW provides automated dual launchers designed to eliminate command-line friction for non-technical field users:

### Option A: Companion Batch Launcher (Easiest)
Double-click `run_dataflow.bat` in the project root folder.
> **Note on Windows Execution Policy:** Windows PowerShell execution policies frequently block unsigned `.ps1` scripts by default (`Restricted`). The `run_dataflow.bat` wrapper automatically bypasses this restriction safely for the local session (`-ExecutionPolicy Bypass -NoProfile`) and invokes `run_dataflow.ps1`.

### Option B: Direct PowerShell Launcher
Open PowerShell in the project directory and run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_dataflow.ps1
```

### What the Launcher Does Automatically:
1. **Checks Python Installation:** Verifies Python 3.11+ is installed on the system PATH.
2. **Initializes Virtual Environment:** Creates a clean `.venv` virtual environment if not already present.
3. **Installs / Updates Dependencies:** Upgrades `pip` and installs pinned production requirements from `requirements.txt`.
4. **Prepares Runtime Directories:** Creates required local runtime paths (`runtime/temporary`, `runtime/exports`, `runtime/audit/diagnostics`, `runtime/audit/overrides`).
5. **Launches Application & Browser:** Starts Streamlit bound strictly to `127.0.0.1:8501` with telemetry disabled and automatically opens your default web browser to the DATAFLOW dashboard.

---

## Manual Installation & CLI Usage

If you prefer setting up the environment manually:

```powershell
# 1. Clone or navigate to the repository
cd d:\DataFlow\dataflow-agent-pack

# 2. Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. (Optional) Install development and testing tools
pip install -r requirements-dev.txt

# 5. Launch the Streamlit interface
streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --browser.gatherUsageStats=false
```

---

## Application Workflow

1. **Upload Data:** Upload raw consolidated Key Population workbook (`.xlsx`, `.xlsm`, `.xlsb`, or `.csv`). Select target population (FSW, MSM, PWID, TG, VP) and reporting period mode (SEM, Q1, Q2).
2. **Processing:** Pipeline executes Ingestion $\rightarrow$ Cleaning $\rightarrow$ DQA Validation $\rightarrow$ Analytics $\rightarrow$ Export generation with live stage timers and memory tracking.
3. **Data Quality Assurance:** Review validation results grouped by severity (Critical, Major, Minor). Critical defects halt reporting unless supervisory override is applied.
4. **Analytics & Cascades:** Inspect pre-computed interactive cascades: HTS Testing Cascade, PrEP Continuum, and Retention/Defined Package breakdowns.
5. **Export Reports:** Download individual modular workbooks or the complete consolidated ZIP package:
   - `01_Summary_<POP>_<PERIOD>.xlsx`
   - `02_Cleaned_Data_<POP>.xlsx` (optional `MASK-XXXX` identifier masking)
   - `03_DQA_Exceptions_<POP>.xlsx`
   - `04_Age_Sex_Disaggregation_<POP>.xlsx`
   - `DATAFLOW_Master_<POP>_<PERIOD>.xlsx`
   - `DATAFLOW_Package_<POP>_<PERIOD>.zip`
6. **Support & Diagnostics:** In the About tab, click "Generate Diagnostic Support Bundle" to produce a sanitized, zero-PII ZIP archive for technical troubleshooting.

---

## Architecture & Project Structure

```
dataflow-agent-pack/
│
├── app.py                      # Main Streamlit application entry point
├── run_dataflow.bat            # Windows batch launcher (ExecutionPolicy bypass)
├── run_dataflow.ps1            # Windows PowerShell automation launcher
├── requirements.txt            # Pinned production dependencies
├── requirements-dev.txt        # Development, testing, and linting dependencies
│
├── core/                       # Ingestion, cleaning, DQA, runner, overrides, diagnostics
│   ├── ingestion.py            # Multi-format Excel ingestion and skiprows detection
│   ├── cleaning.py             # Demographic trimming, upper-casing, date coercions
│   ├── validation.py           # 12 DQA rule engines and severity checks
│   ├── runner.py               # Pipeline orchestrator and SHA-256 caching
│   ├── override.py             # Supervisor HMAC token and DQA exemption manager
│   ├── diagnostics.py          # Zero-PII diagnostic bundle exporter
│   └── compat.py               # Legacy notebook compatibility switches
│
├── analytics/                  # Vectorised indicator calculation engines
│   ├── engine.py               # Cascade orchestrator
│   ├── prep.py / hts.py / art.py / sti.py / tb.py / condoms.py / nsp.py
│   ├── defined_package.py      # Defined Package 1 & 2 pathways
│   └── viral_load.py           # Standardized suppression and LDL categorization
│
├── reporting/                  # Pixel-perfect openpyxl reporting exporters
│   ├── template_manager.py     # YAML-driven visual styles, palettes, fonts
│   ├── excel_exporter.py       # Summary and Age x Sex disaggregation sheets
│   ├── cleaned_data_exporter.py# Streaming write-only cleaned data sheets
│   ├── dqa_exporter.py         # Formatted DQA exceptions sheets
│   └── package_builder.py      # Master workbook and ZIP package assembler
│
├── ui/                         # Streamlit UI presentation pages (zero indicator formulas)
│   ├── dashboard.py / upload.py / processing.py / dqa.py
│   ├── analytics_page.py / export_page.py / config_page.py / about.py
│
├── config/                     # Declarative YAML configurations
│   ├── populations/            # fsw.yaml, msm.yaml, pwid.yaml, tg.yaml, vp.yaml
│   ├── reporting/              # excel_templates.yaml (palettes, fonts, layout specs)
│   └── periods.yaml            # Column-to-period encounter mappings
│
├── tests/                      # Comprehensive automated test suite
│   ├── unit/                   # 180+ unit tests across all modules
│   ├── integration/            # Network isolation, 15-population matrix, error handling
│   └── synthetic/              # Seeded deterministic cohort data generator
│
└── docs/                       # Technical reports, user guide, and specifications
    ├── USER_GUIDE.md           # End-user handbook and provisional indicators appendix
    ├── TROUBLESHOOTING.md      # Field troubleshooting manual
    ├── DECISION_LOG.md         # Formal log of 49 architectural decisions
    └── benchmarks/             # Progressive stress performance report
```

---

## Testing & Quality Assurance

To execute the complete regression test suite:

```powershell
# Run all unit and integration tests
python -m pytest tests/unit tests/integration -v

# Run network isolation socket interception test
python -m pytest tests/integration/test_network_isolation.py -v

# Run 15-combination population x period matrix integration test
python -m pytest tests/integration/test_population_period_matrix.py -v

# Run code style, typing, and formatting checks
python -m ruff check app.py core ui reporting analytics utils scripts tests
python -m ruff format --check app.py core ui reporting analytics utils scripts tests

# Run security dependency vulnerability audit
python -m pip_audit -r requirements.txt
```

---

## Security, Privacy & Compliance

- **Kenya Data Protection Act (2019):** Designed specifically for health data protection. All patient identifiers (UICs, CCC numbers, NUPIs) are processed strictly in-memory or in local encrypted stores.
- **Zero Outbound Sockets:** Rigorously verified via unit and integration tests (`tests/integration/test_network_isolation.py`). The application operates entirely offline with zero external network connectivity.
- **Salted Identifier Masking:** Exported cohort data can be scrubbed using deterministic HMAC-SHA256 pseudo-hashes (`MASK-XXXX`) to facilitate external secondary research without exposing raw patient IDs.
- **Sanitized Diagnostic Bundles:** Technical logs and system environment dumps generated for troubleshooting are scrubbed of all UICs, CCCs, NUPIs, and PE codes via multi-pattern regex redaction.

---

## License & Support

DATAFLOW is proprietary software developed for Key Population HIV prevention and treatment reporting programs. For technical support, bug reports, or feature requests, contact the program M&E technical support team.
