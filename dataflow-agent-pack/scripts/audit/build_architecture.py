#!/usr/bin/env python3
"""Build docs/ARCHITECTURE.md with system architecture, data contracts, and layer separation."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

content = """# ARCHITECTURE — DATAFLOW

Comprehensive architectural specification for DATAFLOW: a high-performance, modular local data management and reporting system.
Audit date: 2026-11-10 | Author: DATAFLOW Engineering Agent | Phase: 0

---

## 1. Architectural Principles

DATAFLOW transforms a legacy, monolithic Jupyter notebook into a robust, decoupled, and verifiable application guided by five core architectural principles:

1. **Strict Separation of Concerns:**
   - `core/`: Pure data ingestion, schema normalization, cleaning, and validation. No Streamlit or presentation dependencies.
   - `analytics/`: Pure functions taking typed DataFrames and config models to compute indicators. Deterministic and state-free.
   - `reporting/`: Openpyxl-based Excel package generation and workbook structure validation.
   - `ui/`: Local Streamlit interface for user interaction. Presentation only—**zero indicator formulas or data manipulation**.
   - `oracle/`: Frozen, bug-compatible copy of the legacy notebook logic used exclusively for differential testing in Phase 4.
2. **Configuration-Driven Business Logic:**
   - All population rules, indicator components, allowed-value vocabularies, and reporting periods live in YAML configuration files validated at load time by typed Pydantic models.
   - Population differences never use hardcoded branching (`if population == "PWID"`).
3. **Auditability & Traceability:**
   - Every transformation writes an audit trail entry (`rule_id`, columns, rows affected).
   - Source data is never modified in-place; inputs are immutable.
   - Run metadata records input SHA-256, config SHA-256, app version, and execution parameters.
4. **Data Privacy & Local Isolation:**
   - Local execution only (`127.0.0.1`). Real data never enters cloud or remote services.
   - Centralized identifier-scrubbing logger guarantees no UICs, names, CCC numbers, or personal data enter logs, tracebacks, or terminal outputs.
5. **Differential Reproducibility:**
   - The engine can reproduce legacy notebook numbers exactly via togglable switches in `config/compat.yaml`.
   - Analytical corrections are introduced one switch at a time with logged diffs.

---

## 2. System Architecture Diagram

```mermaid
flowchart TD
    subgraph UI_Layer [User Interface Layer (Streamlit / CLI)]
        ST_APP["Streamlit Web App (app.py)"]
        CLI_INSP["CLI: inspect <file>"]
        CLI_AGG["CLI: run <file> --aggregate-only"]
    end

    subgraph Config_Layer [Configuration & Schema Models]
        CFG_POP["config/populations/*.yaml"]
        CFG_IND["config/indicators/*.yaml"]
        CFG_VOC["config/vocabularies/*.yaml"]
        CFG_PER["config/reporting/periods.yaml"]
        CFG_TPL["config/reporting/excel_templates.yaml"]
        CFG_MOD["core/config_models.py (Pydantic v2)"]
        CFG_POP & CFG_IND & CFG_VOC & CFG_PER & CFG_TPL --> CFG_MOD
    end

    subgraph Core_Layer [Core Processing Engine]
        INGEST["core/ingestion.py (calamine XLSX/XLS/XLSB)"]
        INSPECT["core/workbook_inspector.py"]
        MAPPER["core/schema_mapper.py"]
        CLEAN["core/cleaning.py (audited cleaning)"]
        DQA["core/validation.py & core/deduplication.py"]
        INGEST --> INSPECT --> MAPPER --> CLEAN --> DQA
    end

    subgraph Analytics_Layer [Analytical Engine]
        IND_ENG["analytics/ (prep, hts, art, sti, tb, condoms, nsp, defined_package)"]
        DEMO_ENG["analytics/demographics.py"]
        KP_ENG["analytics/kplhiv.py & analytics/viral_load.py"]
        SUM_ENG["analytics/summaries.py"]
        DQA --> IND_ENG & DEMO_ENG & KP_ENG
        IND_ENG & DEMO_ENG & KP_ENG --> SUM_ENG
    end

    subgraph Reporting_Layer [Reporting & Package Builder]
        EXCEL_EXP["reporting/excel_exporter.py (Parametrised)"]
        DQA_EXP["reporting/dqa_exporter.py (Exceptions)"]
        CLEAN_EXP["reporting/cleaned_data_exporter.py"]
        PKG_BLD["reporting/package_builder.py (ZIP bundle)"]
        VAL_EXP["reporting/workbook_validator.py"]
        SUM_ENG --> EXCEL_EXP
        DQA --> DQA_EXP
        CLEAN --> CLEAN_EXP
        EXCEL_EXP & DQA_EXP & CLEAN_EXP --> PKG_BLD --> VAL_EXP
    end

    subgraph Testing_Layer [Verification & Quality Assurance]
        SYNTH["tests/synthetic/generator.py (Seeded data)"]
        ORACLE["oracle/ (Legacy reproduction)"]
        DIFF_TEST["tests/differential/ (Engine vs Oracle)"]
        PROP_TEST["tests/property/ (Hypothesis invariant tests)"]
        SYNTH --> ORACLE & Core_Layer
        ORACLE & SUM_ENG --> DIFF_TEST
    end

    UI_Layer --> Core_Layer
    CFG_MOD -.-> Core_Layer & Analytics_Layer & Reporting_Layer
```

---

## 3. Layer Interfaces & Data Contracts

### 3.1 Ingestion Result (`core/ingestion.py`)
```python
@dataclass(frozen=True)
class IngestionResult:
    register_df: pd.DataFrame
    kplhiv_df: pd.DataFrame
    raw_file_hash: str
    file_format: str
    sheet_names: list[str]
    detected_skiprows: int
```

### 3.2 Audit Log Entry (`core/cleaning.py`)
```python
@dataclass(frozen=True)
class AuditEntry:
    rule_id: str
    stage: str
    description: str
    columns_affected: list[str]
    rows_affected: int
    execution_time_ms: float
```

### 3.3 DQA Result & Exception Frame (`core/validation.py`)
```python
@dataclass
class DQAResult:
    total_exceptions: int
    critical_count: int
    major_count: int
    minor_count: int
    exceptions_df: pd.DataFrame  # [rule_id, severity, uic, county, sr_name, region, offending_columns]
    rule_counts: dict[str, int]
```

### 3.4 Summary Result Package (`analytics/summaries.py`)
```python
@dataclass
class SummaryPackage:
    summary_df: pd.DataFrame
    age_group_counts: pd.DataFrame
    kplhiv_summary: pd.DataFrame
    population: str
    period_mode: str
    provisional_indicators: list[str]
```

---

## 4. Privacy & Security Architecture

1. **Identifier Scrubbing Filter:**
   A custom `logging.Filter` intercepts all log records across all modules. It regex-scrubs UICs (`[A-Z0-9]{8,}` patterns), CCC/NUPI numbers, personal names, and dates of birth.
2. **Safe Real-File Operations:**
   - `python -m core.pipeline inspect <file>`: Reads sheet structure, row counts, and column header names only.
   - `python -m core.pipeline run <file> --aggregate-only`: Computes aggregate summary numbers and DQA rule counts. Never prints row-level values or identifiers.
3. **Local Ephemeral Storage:**
   - Temporary processing files reside in `runtime/temporary/` and are deleted immediately upon completion or failure.
   - Final export packages are saved in `runtime/exports/`.

---

## 5. Compatibility Layer (`core/compat.py`)

To satisfy the differential testing requirement (Master Brief §5.6 / §9), `config/compat.yaml` defines feature flags that emulate legacy behaviors:
- `legacy_missing_age_below_15`: Routes NaN age to `'Below 15'` instead of `'Unknown'`.
- `legacy_impute_missing_sex_f`: Replaces missing sex with `'F'`.
- `legacy_row_sum_flags`: Sums row-propagated flags across duplicate rows rather than unique UICs.
- `legacy_hts_sem_month_ge_7`: Evaluates `enrolled_month >= 7` without year checking.
- `legacy_comment_out_pwid_nsp`: Excludes NSP from PWID Defined Package.

Phase 4 differential testing proves the new engine matches the legacy notebook with 100% precision with all switches enabled, before switching them off one by one with Owner approval.
"""


def main():
    out_path = BASE_DIR / "docs" / "ARCHITECTURE.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Written docs/ARCHITECTURE.md ({len(content.splitlines())} lines)")


if __name__ == "__main__":
    main()
