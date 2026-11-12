# TG CORRECTIONS LOG — DATAFLOW

**Date:** 2026-11-12  
**Dataset:** Real-World Transgender (`reference/Consolidated TG.xlsb`)  
**Scope:** Architectural and Implementation Corrections Log (Phase F)  

---

## 1. Overview of Corrections

All code modifications were made strictly to resolve identified root causes in data cleaning, clinical status vocabulary matching, indicator disaggregation, and reporting presentation. No expected figures or benchmark values were hardcoded; all indicators are calculated dynamically from raw client encounters.

---

## 2. File-by-File Modification Log

### 2.1 `core/cleaning.py`
- **Function Corrected:** `parse_date_series(series: pd.Series) -> pd.Series`
- **Root Cause:**
  1. The regex pattern `^\d{4}-\d{2}-\d{2}$` required exact string termination after the day digits, failing on ISO datetime strings containing timestamps (e.g. `'2023-09-08 00:00:00'`).
  2. Unparsed strings fell through to `pd.to_datetime(s[non_iso], dayfirst=True)`. Pandas locked into `%Y-%d-%m %H:%M:%S` based on early rows, swapping month/day on dates $\le 12$ and coercing any date where day $> 12$ to `NaT`.
  3. Excel numeric serial numbers (e.g. `37422` in Date of Birth) failed parsing without origin conversion.
- **Implementation Changes:**
  - Expanded regex to match optional time components: `r"^\d{4}-\d{2}-\d{2}(?:[ T].*)?$"`, extracting the 10-character `YYYY-MM-DD` substring for fast deterministic parsing.
  - Added dedicated numeric serial conversion via `pd.to_datetime(serials, unit="D", origin="1899-12-30")` for serial strings prior to fallback day-first parsing.
- **Outcome:**
  - `date_of_enrolment` missing count dropped from 2,029 to 0.
  - `date_of_birth_dd_mm_yyyy_` missing count dropped from 112 to 0.
  - Eliminated 2,141 false-positive DQA exceptions.

---

### 2.2 `analytics/art.py`
- **Function Corrected:** `compute_art_indicators(df: pd.DataFrame, compat: CompatSwitches | None = None) -> pd.DataFrame`
- **Root Cause:**
  When `compat.legacy_capitalize_vocabulary` was `True`, `known_pos_variants` was restricted strictly to `["Known positive"]` (lowercase 'p') and case-sensitivity was enforced. In the TG dataset, the clinical entry is `"Known Positive"` (capital 'P'). This prevented the affirmative identification of `plhiv = 1`.
  Because `plhiv` was 0, `plhivservice_q1` was 0, omitting all 86 eligible known-positive clients from the Defined Package PLHIV pathway.
- **Implementation Changes:**
  Expanded `known_pos_variants` to include `["Known positive", "Known Positive", "known positive", "KNOWN POSITIVE"]`.
- **Outcome:**
  - `plhiv` identified all 100 known-positive clients.
  - `plhivservice_q1` qualified all 86 eligible PLHIV clients.
  - `DefinedPackage_Q1` reconciled from 2,965 to 3,051 across all 16 counties (100% agreement).

---

### 2.3 `analytics/prep.py`
- **Function Corrected:** `compute_prep_indicators(df: pd.DataFrame, compat: CompatSwitches | None = None) -> pd.DataFrame`
- **Root Cause:**
  PrEP status matching in quarterly columns looked only for capitalized terms (`["Initiated", "Restart", "Switched", "Refill"]`). In Kajiado County (Sub-Recipient HWWK), a client record carried lowercase `'switched'`, which was excluded under case-sensitive evaluation.
- **Implementation Changes:**
  Expanded `active_prep`, `refill_variants`, `initiate_variants`, and `disc_variants` to include standard title-case and lower-case variants.
- **Outcome:**
  - Client `34/185/922/HWW/27/06/ANMUMA/6/24` correctly qualified for `prep_q1`.
  - PrEP in Kajiado HWWK reconciled from 60 to 61 (100% agreement).

---

### 2.4 `analytics/demographics.py`
- **Function Added:** `compute_kpi_demographic_summary(df: pd.DataFrame, period_mode: str = "Q1", compat: CompatSwitches | None = None) -> pd.DataFrame`
- **Root Cause:**
  The system previously lacked an engine function to compute the 24-column multi-indicator KPI Age x Sex table defined in notebook Cell 84 and present in `Summary TG.xlsx` sheet `KPI`.
- **Implementation Changes:**
  - Implemented client-level age grouping (`15-19`, `20-24`, `25+`, `Below 15`, `Unknown`).
  - Standardized biological sex with M/F mapping.
  - Created composite age-sex keys (`15-19_M`, `15-19_F`, etc.).
  - Computed pivot aggregations across `DEFINED PACKAGE`, `HTS`, and `PREP`.
  - Generated `{indicator}_Total` columns and structured the 24-column DataFrame grouped by `['sr_name', 'region', 'county']`.
- **Outcome:**
  Enabled end-to-end automated generation of the legacy KPI demographic sheet.

---

### 2.5 `reporting/excel_exporter.py`
- **Function Corrected:** `export_age_sex_disaggregation_sheet(workbook, sheet_name, register_df, period_mode="Q1", config=None)`
- **Root Cause:**
  Previously, `export_age_sex_disaggregation_sheet` only exported a stub table containing 3 geography columns and client counts, completely missing the 21 KPI indicator demographic columns and multi-tier merged headers.
- **Implementation Changes:**
  - Redesigned openpyxl worksheet generator to build the exact layout of legacy sheet `KPI`.
  - Rendered Row 1 multi-level merged headers: `DEMOGRAPHICS` (cols 1–3, green `#00B050`), `DEFINED PACKAGE` (cols 4–10, blue `#0070C0`), `HTS` (cols 11–17, orange `#F79646`), and `PREP` (cols 18–24, peach `#FCD5B5`).
  - Rendered Row 2 subheaders (`SR  NAME`, `REGION`, `COUNTY`, and the 7 age-sex categories per indicator).
  - Populated data rows with zebra striping and bold totals.
  - Rendered `TOTAL` row with merged label and dynamic `=SUM()` formulas.
- **Outcome:**
  100% pixel-perfect concordance with legacy sheet `KPI` (0 cell differences).

---

### 2.6 `reporting/package_builder.py`
- **Function Corrected:** `build_reporting_package(...)`
- **Implementation Changes:**
  - Defined `pop_str = population.upper()` and `period_str = period_mode.upper()` in function scope.
  - Added Tab 7 (`KPI` / `KPI_Disaggregation`) to the master workbook `DATAFLOW_Master_TG_Q1.xlsx`.
  - Configured standalone disaggregation workbook `04_Age_Sex_Disaggregation_TG.xlsx` to use sheet title `"KPI"` for TG.
- **Outcome:**
  Both Master and modular workbooks contain complete, verified KPI summary sheets.

---

### 2.7 `core/runner.py` & `ui/analytics.py`
- **Changes in `core/runner.py`:**
  - Pre-computed `kpi_summary_df` during Stage 4 Analytics.
  - Added `kpi_summary_df` to `display_analytics` dictionary.
- **Changes in `ui/analytics.py`:**
  - Added Section 6 rendering `kpi_summary_df` in Streamlit UI directly from pre-computed analytics (maintaining zero business logic in UI).
- **Outcome:**
  UI displays the complete KPI demographic breakdown alongside service summaries.
