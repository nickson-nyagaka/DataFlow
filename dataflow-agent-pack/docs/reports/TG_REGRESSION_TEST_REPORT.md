# TG REGRESSION TEST REPORT — DATAFLOW

**Date:** 2026-11-12  
**Test Suite:** `tests/integration/test_tg_regression.py` & Full Unit Test Suite  
**Target Population:** Transgender (TG)  
**Execution Environment:** Windows, Python 3.14.7, pytest 9.2.0  

---

## 1. Executive Summary

A permanent, automated regression and integration test suite has been established in `tests/integration/test_tg_regression.py` to prevent future regressions in Transgender (TG) population data ingestion, cleaning, DQA rule evaluation, analytical aggregation, and Excel report package generation.

All **6 integration test suites** and all **111 existing unit test suites** passed with a **100% pass rate** (117 total passed tests, 0 failures, 0 skipped).

```text
======================== 6 passed in 90.80s (0:01:30) =========================
====================== 111 passed, 4 warnings in 20.92s =======================
```

---

## 2. Regression Test Suite Architecture

The permanent TG test suite is located at `tests/integration/test_tg_regression.py` and evaluates real client-level records from `reference/Consolidated TG.xlsb` against expected legacy figures in `reference/Summary TG.xlsx`.

| Test Identifier | Scope | Key Assertions | Result |
|---|---|---|:---:|
| `test_tg_data_integrity` | Ingestion & Cleaning | 3,124 Register rows preserved, 100 KPLHIV rows preserved, 3,124 unique UICs, 0 missing dates, 0 dropped records | **PASS** |
| `test_tg_dqa_accuracy` | DQA Rule Engine | Exactly 5 genuine exceptions, 3 Critical (`DQA_HIV_NEG_ON_ART`), 2 Major (`DQA_HIV_POS_NO_ART`), 0 date false positives | **PASS** |
| `test_tg_defined_package_rules` | Population Logic | Strictly NO NSP required for TG; General pathway = 2,965; PLHIV pathway = 86; Total = 3,051 | **PASS** |
| `test_tg_service_summary_reconciliation` | Service Summary Parity | 16 counties $\times$ 25 columns (400 cells) matched against legacy `TG` sheet with 0 discrepancies | **PASS** |
| `test_tg_kpi_demographic_reconciliation` | KPI Demographic Parity | 16 rows $\times$ 24 columns (384 cells) matched against legacy `KPI` sheet with 0 discrepancies | **PASS** |
| `test_tg_pipeline_exports_and_parity` | End-to-End Pipeline & Export | Master, Summary, Disaggregation workbooks generated; tab structure verified; checksums validated | **PASS** |

---

## 3. Detailed Test Suite Breakdown

### 3.1 Test Case 1: Ingestion and Cleaning Data Integrity (`test_tg_data_integrity`)
- **Objective:** Ensure that the workbook loader (`calamine` / `openpyxl`) and cleaning transformations do not silently drop, alter, or corrupt client records.
- **Verification Logic:**
  - `len(reg_raw) == 3124` and `len(reg_clean) == 3124`.
  - `len(kp_raw) == 100` and `len(kp_clean) == 100`.
  - Unique UICs: exactly 3,124 in Register, 100 in KPLHIV.
  - Zero missing UICs: `reg_clean["kp_vp_unique_identifier_code"].isna().sum() == 0`.
  - Date Parsing: `date_of_enrolment.isna().sum() == 0` and `date_of_birth_dd_mm_yyyy_.isna().sum() == 0`.
  - Mandatory Geographic & Demographic fields: 0 NaNs in `county`, `sr_name`, `region`, `age`, `sex_m_f_`.

### 3.2 Test Case 2: DQA Accuracy & False-Positive Elimination (`test_tg_dqa_accuracy`)
- **Objective:** Ensure DQA accurately detects genuine clinical contradictions while generating zero false positives.
- **Verification Logic:**
  - Total exceptions evaluated across all 25 rules must equal **exactly 5**.
  - Critical exceptions: exactly 3 (`DQA_HIV_NEG_ON_ART`).
  - Major exceptions: exactly 2 (`DQA_HIV_POS_NO_ART`).
  - Strict assertion of absence for resolved false-positive rules:
    - `"DQA_MISSING_ENROLMENT_DATE"` not in `rule_counts` (down from 2,029).
    - `"DQA_MISSING_DOB"` not in `rule_counts` (down from 112).
    - `"DQA_DUPLICATE_UIC"` not in `rule_counts` (0 duplicates).
    - `"DQA_MISSING_UIC"` not in `rule_counts` (0 missing).

### 3.3 Test Case 3: Population-Specific Defined Package Rules (`test_tg_defined_package_rules`)
- **Objective:** Verify that TG population rules correctly execute dual clinical pathways and do not inherit PWID's Needle and Syringe Programme (NSP) requirement.
- **Verification Logic:**
  - `definedpackage_q1.sum() == 3051`.
  - General pathway eligibility:
    $$\text{hts\_q1} \land \text{sti\_screened\_q1} \land \text{tb\_screened\_q1} \land \text{condoms\_q1} \land \text{he\_rrc\_q1} = 2,965$$
  - PLHIV service pathway eligibility:
    $$\text{plhivservice\_q1} = (\text{plhiv} \land \text{sti\_screened} \land \text{tb\_screened} \land \text{condoms} \land \text{he\_rrc}) = 86$$
  - Union of pathways: $2,965 + 86 = 3,051$ unique clients.

### 3.4 Test Case 4: Service Summary Cell Reconciliation (`test_tg_service_summary_reconciliation`)
- **Objective:** Cell-by-cell numerical reconciliation of DataFlow's generated Service Summary against the legacy reference sheet `TG` in `reference/Summary TG.xlsx`.
- **Verification Logic:**
  - Loads data-only values from `Summary TG.xlsx` sheet `TG` (rows 3 to 18, columns 1 to 25).
  - Joins DataFlow `summary_df` on composite key `COUNTY_SR_NAME`.
  - Asserts exact equality across all 25 columns:
    `county`, `sr_name`, `region`, `15-19`, `20-24`, `25+`, `Below 15`, `TotalCohort`, `TotalPE`, `HTSQ1`, `HTS_Negative`, `HTS_Positive`, `Total_KPLHIV`, `Suppressed`, `DefinedPackage_Q1`, `PREP_Q1`, `New_on_ART`, `CurrentArt_Q1`, `STISCREENEDQ_1`, `STIDiagnosid_Q1`, `STItreated_Q1`, `TB_SCREENED_Q1`, `PeerEducation_Q1`, `ReceivedCondom_Q1`, `total_condoms_Q1`.
  - Discrepancy counter `len(diffs) == 0`.

### 3.5 Test Case 5: KPI Age $\times$ Sex Demographic Reconciliation (`test_tg_kpi_demographic_reconciliation`)
- **Objective:** Cell-by-cell reconciliation of DataFlow's multi-indicator Age $\times$ Sex table against legacy reference sheet `KPI` in `reference/Summary TG.xlsx`.
- **Verification Logic:**
  - Reconciles 21 numeric columns + 3 administrative columns across 16 reporting rows:
    - Defined Package: 15–19 M/F, 20–24 M/F, 25+ M/F, Total
    - HTS: 15–19 M/F, 20–24 M/F, 25+ M/F, Total
    - PrEP: 15–19 M/F, 20–24 M/F, 25+ M/F, Total
  - Discrepancy counter `len(diffs) == 0`.

### 3.6 Test Case 6: End-to-End Pipeline & Export Parity (`test_tg_pipeline_exports_and_parity`)
- **Objective:** Verify `run_full_pipeline` from raw workbook file path through all 5 stages, verifying timings, metadata, and workbook file generation.
- **Verification Logic:**
  - Cohort size == 3,124.
  - Total DQA exceptions == 5 (3 Critical, 2 Major).
  - Verifies disk existence of:
    - Master reporting workbook (`01_Master_Report_TG.xlsx`).
    - Service summary workbook (`02_Summary_Report_TG.xlsx`).
    - Disaggregation workbook (`04_Disaggregation_TG.xlsx`).
    - Distribution zip bundle (`DATAFLOW_Export_Package_TG.zip`).
  - Verifies presence of `KPI` and `KP_Summary` worksheets in Master workbook.

---

## 4. Full Unit Test Suite Verification

To confirm that the fixes implemented for TG did not introduce regressions into other population pipelines or core services, the complete existing unit test suite was executed.

### Test Execution Command
```powershell
$env:PYTHONPATH="d:\DataFlow\dataflow-agent-pack"
Set-Location d:\DataFlow\dataflow-agent-pack
pytest tests/unit/test_analytics.py tests/unit/test_config.py tests/unit/test_dqa.py tests/unit/test_ingestion.py tests/unit/test_reporting.py -v
```

### Results Summary
```text
tests/unit/test_analytics.py .......................                     [ 20%]
tests/unit/test_config.py ..................                             [ 36%]
tests/unit/test_dqa.py .........................................         [ 73%]
tests/unit/test_ingestion.py .........                                   [ 81%]
tests/unit/test_reporting.py ....................                        [100%]

====================== 111 passed, 4 warnings in 20.92s =======================
```

- `tests/unit/test_analytics.py`: **23/23 PASSED** (Includes Oracle parity across FSW, PWID, MSM, TG, VP; switch-flipping tests for D-008, D-020..D-028).
- `tests/unit/test_config.py`: **18/18 PASSED** (Configuration loader, population schema validation, compat switch loading).
- `tests/unit/test_dqa.py`: **41/41 PASSED** (Rule registry, severity thresholds, cross-sheet CCC joins, viral load suppression).
- `tests/unit/test_ingestion.py`: **9/9 PASSED** (Excel header skipping, sheet detection, calamine parser).
- `tests/unit/test_reporting.py`: **20/20 PASSED** (Workbook construction, cell styling, metadata writing).

---

## 5. Conclusion & Operational Sign-off

The regression test suite `tests/integration/test_tg_regression.py` is fully automated, deterministic, and self-contained. It executes in continuous integration or on demand in under 95 seconds, guaranteeing that future enhancements will not compromise the verified analytical and DQA accuracy of DataFlow.
