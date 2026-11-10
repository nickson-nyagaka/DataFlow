#!/usr/bin/env python3
"""Build docs/IMPLEMENTATION_PLAN.md with detailed roadmap for Phase 1."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

content = r"""# IMPLEMENTATION PLAN — DATAFLOW (Phase 1 Focus)

Detailed execution plan, file inventory, risk management, and testing strategy for Phase 1.
Audit date: 2026-11-10 | Author: DATAFLOW Engineering Agent | Phase: 0

---

## 1. Overview & Objectives for Phase 1

Phase 1 establishes the foundational infrastructure, validated YAML configuration schemas, a deterministic synthetic data generator planting realistic edge cases, and a callable bug-compatible `oracle/` package replicating the legacy notebook.

**Phase 1 Goal:** A solid skeleton, validated configuration, trustworthy fake data, and a runnable copy of the notebook logic to test against.
**May Touch in Phase 1:** Everything except `reference/` and `docs/gates/`.

---

## 2. Work Breakdown Structure (Phase 1)

### Work Package 1.1: Project Skeleton & Dependency Management
- **Files to create:**
  - `pyproject.toml`: ruff (lint + format), pytest configuration.
  - `requirements.txt`: exact pins for runtime dependencies (`pandas==2.2.3`, `numpy==2.1.3`, `python-calamine==0.2.3`, `openpyxl==3.1.5`, `pydantic==2.10.2`, `pyyaml==6.0.2`, `streamlit==1.40.1`, `plotly==5.24.1`).
  - `requirements-dev.txt`: exact pins for development and testing (`pytest==8.3.3`, `pytest-cov==6.0.0`, `hypothesis==6.120.3`, `ruff==0.8.0`).
  - `.streamlit/config.toml`: `server.address = "127.0.0.1"`, `browser.gatherUsageStats = false`, max upload 200MB.
  - Directory structure: `config/`, `core/`, `analytics/`, `reporting/`, `ui/`, `utils/`, `oracle/`, `tests/synthetic/`, `runtime/temporary/`, `runtime/exports/`, `runtime/logs/`.
- **Exit Evidence:** Clean `pip install -r requirements.txt` and `pip install -r requirements-dev.txt`.

### Work Package 1.2: Configuration Models & Population YAMLs
- **Files to create:**
  - `core/config_models.py`: Strongly typed Pydantic v2 schemas:
    - `PopulationConfig`: `code`, `name`, `sheet_aliases`, `skiprows`, `require_nsp_defined_package`, `include_nsp_block`, `sheet_titles`.
    - `PeriodConfig`: `period_name`, `quarter_mappings`, `column_regexes`.
    - `VocabularyConfig`: `field_name`, `canonical_values`, `case_variants`.
  - `config/settings.yaml`: Global defaults, execution timeouts, logging levels.
  - `config/compat.yaml`: Initial legacy switches (all defaulting to `true` for oracle parity, `false` for target engine).
  - Population YAML files:
    - `config/populations/fsw.yaml`
    - `config/populations/msm.yaml`
    - `config/populations/tg.yaml`
    - `config/populations/pwid.yaml` (NSP required in Defined Package per BR-001)
    - `config/populations/vp.yaml`
  - Vocabulary and period skeletons: `config/vocabularies/*.yaml`, `config/reporting/periods.yaml`.
- **Negative Testing:** Write `>= 10` negative unit tests proving invalid YAMLs fail loudly with filename and invalid key in exception.

### Work Package 1.3: Privacy-Safe Logger & Exception Hierarchy
- **Files to create:**
  - `utils/logger.py`: Implements `IdentifierScrubbingFilter(logging.Filter)` scrubbing UIC patterns, phone numbers, CCC numbers, names, and DOBs from all logs and tracebacks.
  - `core/exceptions.py`: Domain exception hierarchy (`DataFlowError`, `ConfigValidationError`, `IngestionError`, `SchemaMismatchError`, `DQAError`, `AnalyticalError`).
- **Test Evidence:** Test passing 100 known planted UIC strings and names through logger and verifying zero occurrences in log output or formatted tracebacks.

### Work Package 1.4: Synthetic Data Generator (`tests/synthetic/generator.py`)
- **Objective:** Pure, deterministic generator capable of producing realistic Register and KPLHIV sheets for all 5 populations with planted defects for testing.
- **Planted Defects (per Master Brief §13.1):**
  1. Duplicate UICs (multi-row encounters).
  2. Mixed-case status strings (`Known positive`, `Known Positive`, `POSITIVE`, `positive`).
  3. Excel float artifacts on IDs (`12345.0` -> `12345`).
  4. Missing values in key fields (age, sex, county, sr_name).
  5. Diverse viral load formats: `LDL`, `<LDL`, `>LDL`, `9250cp/ml`, `1,200`, `UNKNOWN`, unparseable junk.
  6. Clinical anomalies: Negative on ART, Positive without ART, TB/STI diagnosed without screening.
  7. Multi-column sort traps: $\ge 10$ visit columns to verify lexicographic sort failure (`_10` vs `_2`).
  8. Missing geography (`NaN` county/SR/region).
  9. CCC number mismatches (Register clients not in KPLHIV and vice versa).
- **Deliverable:** Generator CLI emitting synthetic `.xlsx` / `.xlsb` workbooks and a companion `ground_truth.json` containing exact counts of planted defects.

### Work Package 1.5: Oracle v0 Implementation (`oracle/`)
- **Objective:** A clean, importable Python transcription of the notebook logic that runs without Jupyter, absolute paths, or GUI prompts.
- **Files to create:**
  - `oracle/legacy_clean.py`: Exact reproduction of notebook cell 14 and cell 21 string operations.
  - `oracle/legacy_dqa.py`: Exact reproduction of notebook cells 34, 36, 38, 40, 42, 52.
  - `oracle/legacy_indicators.py`: Exact reproduction of notebook cell 61 indicator formulas (including `any_in_unique_allrows` and positional column slicing).
  - `oracle/legacy_summaries.py`: Exact reproduction of notebook cells 54, 66, 69.
  - `oracle/legacy_exporter.py`: Exact reproduction of notebook openpyxl export logic.
- **Test Evidence:** Run oracle end-to-end on synthetic FSW and PWID workbooks, verifying successful emission of summary DataFrames.

### Work Package 1.6: Gate Check Suite
- **Files to create:**
  - `tests/unit/test_gate_check.py`: Tests for `scripts/gate_check.py` validating that:
    - Status parsing is correct across all 8 phases.
    - Out-of-sequence approvals raise immediate hard errors.
    - Command-line argument verification (`gate_check.py N`) behaves as specified.

---

## 3. Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Python-calamine XLSB compatibility** | Inability to parse complex binary Excel files | Calamine engine is benchmarked in Phase 1 against synthetic XLSB files; fallback to `pyxlsb` if edge cases arise. |
| **Pydantic v2 migration nuances** | Breaking changes in model validation | Strict pinned version (`pydantic==2.10.2`) with comprehensive schema unit tests. |
| **Synthetic data generator skew** | Oracle fails on synthetic data due to missing columns | Generator schema is derived directly from the column inventory documented in Phase 0. |

---

## 4. Phase 1 Exit Checklist

- [ ] All 5 population YAMLs load and validate cleanly against Pydantic models.
- [ ] $\ge 10$ negative configuration tests assert failure with file and key in message.
- [ ] Logger test verifies 100 planted UICs never appear in captured logs.
- [ ] Generator is deterministic (same seed -> identical file SHA-256) and emits `ground_truth.json`.
- [ ] Oracle runs end-to-end on synthetic FSW and PWID data without error.
- [ ] `gate_check.py` unit tests pass.
- [ ] `ruff check .` clean, `ruff format --check .` clean, `pytest` green.
"""


def main():
    out_path = BASE_DIR / "docs" / "IMPLEMENTATION_PLAN.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Written docs/IMPLEMENTATION_PLAN.md ({len(content.splitlines())} lines)")


if __name__ == "__main__":
    main()
