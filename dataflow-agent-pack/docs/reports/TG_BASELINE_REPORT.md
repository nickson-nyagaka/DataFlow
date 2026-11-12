# TG BASELINE AUDIT REPORT — DATAFLOW

**Date:** 2026-11-12  
**Dataset:** Real-World Transgender (`reference/Consolidated TG.xlsb`)  
**Status:** Mandatory Baseline Assessment (Phase B — Prior to any Code Modifications)  

---

## 1. Executive Summary

This baseline report captures the operational performance, DQA exception profile, and analytical concordance of the DATAFLOW application when executed against the real-world Transgender (TG) dataset prior to any implementation modifications.

While the core pipeline completes all 5 stages without fatal crashes, the audit revealed three major defects:
1. **Severe DQA False Positive Inflation:** 2,141 false-positive DQA exceptions were generated (2,029 for `DQA_MISSING_ENROLMENT_DATE` and 112 for `DQA_MISSING_DOB`) caused by datetime parsing failure on ISO strings with time components (`YYYY-MM-DD HH:MM:SS`) and Excel numeric serial numbers.
2. **Defined Package Under-Counting:** Defined Package was under-counted by 86 clients (2,965 vs. expected 3,051) across 14 of the 16 reporting counties due to strict case-sensitive vocabulary matching failing on `"Known Positive"` (capital P), which erroneously suppressed the entire PLHIV service pathway.
3. **PrEP Under-Counting:** PrEP coverage was under-counted by 1 client in Kajiado HWWK (60 vs. expected 61) due to case-sensitive vocabulary matching failing on lowercase `'switched'`.
4. **Missing KPI Demographic Disaggregation Sheet:** The exported demographic workbook did not render the legacy 24-column multi-indicator KPI Age x Sex table (`DEFINED PACKAGE`, `HTS`, and `PREP` disaggregated across `15-19_M`, `15-19_F`, `20-24_M`, `20-24_F`, `25+_M`, `25+_F`, and `Total`).

---

## 2. Ingestion and Cleaning Baseline Results

### 2.1 Ingestion
- **Input File:** `reference/Consolidated TG.xlsb` (1,038,470 bytes)
- **Engine Used:** `pyxlsb` / `calamine`
- **Register Sheet:** Ingested 3,124 client rows × 337 columns (`skiprows=2`).
- **KPLHIV Sheet:** Ingested 100 rows × 72 columns (`skiprows=2`).
- **Identifier Integrity:** 3,124 distinct UICs in Register; 100 distinct UICs in KPLHIV. Exactly 100 distinct CCC numbers in both sheets with zero cross-sheet CCC discrepancies. Zero records dropped.

### 2.2 Cleaning Anomalies (Root Cause of False Positives)
In `core/cleaning.py::parse_date_series`:
- Raw `date_of_enrolment` has **0 missing values** (all 3,124 records have valid timestamps such as `'2023-09-08 00:00:00'`).
- Cleaned `date_of_enrolment` has **2,029 null (NaN/NaT) values**!
- Raw `date_of_birth_dd_mm_yyyy_` has **0 missing values** (stored as ISO strings, DD/MM/YYYY, or Excel serial numbers such as `37422`).
- Cleaned `date_of_birth_dd_mm_yyyy_` has **112 null values**!

**Mechanism:**  
The ISO regex `^\d{4}-\d{2}-\d{2}$` did not match strings containing time components (`' 00:00:00'`). Unmatched strings fell through to `pd.to_datetime(s[non_iso], dayfirst=True, errors="coerce")`. Because early elements had day $\le 12$, pandas locked into `%Y-%d-%m %H:%M:%S` (Year-Day-Month), transposing months and days, and subsequently coercing any date where the third token exceeded 12 (e.g. `'2023-09-13 00:00:00'`) to `NaT`.

---

## 3. Baseline DQA Audit Results

### 3.1 Exception Summary
- **Total Exceptions Flagged:** 2,146
- **Critical Severity:** 3
- **Major Severity:** 2,143
- **Minor Severity:** 0

### 3.2 Breakdown by Rule
| DQA Rule ID | Rule Name | Severity | Evaluated | Flagged | Genuine / False Positive |
|---|---|---|---:|---:|---|
| `DQA_DUPLICATE_UIC` | Duplicate UIC in Register | Critical | 3,124 | 0 | Valid (0 duplicates) |
| `DQA_MISSING_UIC` | Missing Client UIC | Critical | 3,124 | 0 | Valid (0 missing) |
| `DQA_MISSING_COUNTY` | Missing County Geography | Critical | 3,124 | 0 | Valid (0 missing) |
| `DQA_MISSING_SR_NAME` | Missing Sub-Recipient Name | Critical | 3,124 | 0 | Valid (0 missing) |
| `DQA_HIV_NEG_ON_ART` | HIV Negative on ART | Critical | 3,124 | 3 | **Genuine Critical Exception** |
| `DQA_PREP_ON_POSITIVE` | PrEP on HIV Positive Client | Critical | 3,124 | 0 | Valid (0 violations) |
| `DQA_CCC_REG_NOT_KPLHIV` | Register CCC Missing in KPLHIV | Critical | 100 | 0 | Valid (100% matched) |
| `DQA_HIV_POS_NO_ART` | HIV Positive Not on ART | Major | 3,124 | 2 | **Genuine Major Exception** |
| `DQA_TB_UNSCREENED` | TB Diagnosed Without Screening | Major | 3,124 | 0 | Valid |
| `DQA_STI_UNSCREENED` | STI Diagnosed/Treated Unscreened | Major | 3,124 | 0 | Valid |
| `DQA_MULTIPLE_PREP_INITIATIONS` | Multiple PrEP Initiations | Major | 3,124 | 0 | Valid |
| `DQA_CCC_KPLHIV_NOT_REG` | KPLHIV CCC Missing in Register | Major | 100 | 0 | Valid (100% matched) |
| `DQA_MISSING_AGE` | Missing Client Age | Major | 3,124 | 0 | Valid (0 missing) |
| `DQA_MISSING_SEX` | Missing Biological Sex | Major | 3,124 | 0 | Valid (0 missing) |
| `DQA_MISSING_DOB` | Missing Date of Birth | Major | 3,124 | 112 | **False Positive (Parsing Defect)** |
| `DQA_MISSING_ENROLMENT_DATE` | Missing Date of Enrolment | Major | 3,124 | 2,029 | **False Positive (Parsing Defect)** |
| `DQA_MISSING_PE_CODE` | Missing Peer Educator Code | Major | 3,124 | 0 | Valid (0 missing) |

### 3.3 Clinical Audit of Genuine Exceptions
1. **`DQA_HIV_NEG_ON_ART` (3 cases):**
   - UIC `45/269/1344/IRD/04/ELNYOT/02/0068`: Tested HIV-Negative; received PrEP (1 month dispensed); erroneously recorded as `currently_on_art = Yes`.
   - UIC `45/269/1344/IRD/04/ELMOMA/02/0153`: Tested HIV-Negative; received PrEP (1 month dispensed); erroneously recorded as `currently_on_art = Yes`.
   - UIC `45/269/1344/IRD/04/ESKIOK/01/0112`: Tested HIV-Negative; received PrEP (1–2 months dispensed); erroneously recorded as `currently_on_art = Yes` and `art_outcome = Active`.
   *Assessment:* Legitimate clinical conflict. Clients are active PrEP users; ART status was incorrectly recorded as affirmative.

2. **`DQA_HIV_POS_NO_ART` (2 cases):**
   - UIC `32/176/878/HWW/14/04/BENJWA/6/31`: Known Positive; on ART in Month 1; defaulted in Month 2 (`currently_on_art = No`, `art_outcome = Defaulter`); resumed in Month 3.
   - UIC `32/176/878/HWW/10/04/BRWA00/7/20`: Known Positive; on ART in Month 1; defaulted in Month 2 (`currently_on_art = No`, `art_outcome = Defaulter`); resumed in Month 3.
   *Assessment:* Legitimate clinical tracking finding. Reflects actual treatment default during the quarter.

---

## 4. Analytical Concordance Baseline Results

### 4.1 Service Summary (`Summary TG.xlsx` Sheet: `TG`)
Comparison between current DataFlow `summary_df` and legacy sheet `TG` (16 rows × 25 columns = 400 cells):
- **Matching Cells:** 385 / 400 (96.25%)
- **Discrepant Cells:** 15 / 400 (3.75%)

#### Discrepancies by Row and Indicator:
| County & SR | Indicator | Legacy Expected | DataFlow Baseline | Numerical Variance | Root Cause |
|---|---|---:|---:|---:|---|
| Bungoma MAAYGO | DEFINED PACKAGE | 517 | 503 | -14 | Case sensitivity missed `"Known Positive"` |
| Kajiado HOYMAS | DEFINED PACKAGE | 144 | 143 | -1 | Case sensitivity missed `"Known Positive"` |
| Kajiado HWWK | DEFINED PACKAGE | 210 | 202 | -8 | Case sensitivity missed `"Known Positive"` |
| Kajiado HWWK | PREP | 61 | 60 | -1 | Case sensitivity missed lowercase `'switched'` |
| Kakamega MAAYGO | DEFINED PACKAGE | 215 | 207 | -8 | Case sensitivity missed `"Known Positive"` |
| Kilifi AMKENI-MALINDI | DEFINED PACKAGE | 384 | 375 | -9 | Case sensitivity missed `"Known Positive"` |
| Kisii IRDO | DEFINED PACKAGE | 153 | 146 | -7 | Case sensitivity missed `"Known Positive"` |
| Kwale PUP-AMKENI | DEFINED PACKAGE | 100 | 88 | -12 | Case sensitivity missed `"Known Positive"` |
| Laikipia BHESP | DEFINED PACKAGE | 185 | 183 | -2 | Case sensitivity missed `"Known Positive"` |
| Migori IRDO | DEFINED PACKAGE | 290 | 283 | -7 | Case sensitivity missed `"Known Positive"` |
| Nairobi ISHTAR | DEFINED PACKAGE | 129 | 124 | -5 | Case sensitivity missed `"Known Positive"` |
| Nakuru HWWK | DEFINED PACKAGE | 110 | 107 | -3 | Case sensitivity missed `"Known Positive"` |
| Siaya MAAYGO | DEFINED PACKAGE | 106 | 102 | -4 | Case sensitivity missed `"Known Positive"` |
| Uasin Gishu NIAK | DEFINED PACKAGE | 46 | 45 | -1 | Case sensitivity missed `"Known Positive"` |
| Vihiga MAAYGO | DEFINED PACKAGE | 132 | 127 | -5 | Case sensitivity missed `"Known Positive"` |

### 4.2 KPI Demographic Summary (`Summary TG.xlsx` Sheet: `KPI`)
- **Legacy Layout:** 16 rows × 24 columns covering `DEMOGRAPHICS` (SR, Region, County), `DEFINED PACKAGE` (7 age-sex categories), `HTS` (7 age-sex categories), and `PREP` (7 age-sex categories).
- **DataFlow Baseline:** The existing `export_age_sex_disaggregation_sheet()` in `reporting/excel_exporter.py` did not compute or export this structure at all; it produced a stub with only geographic keys and row client counts.

---

## 5. Performance and Resource Baseline

| Metric | Measured Baseline Value |
|---|---|
| Total Pipeline Runtime (without memory profiler) | 43.08 seconds |
| Ingestion Stage Duration | 2.01 seconds |
| Cleaning Stage Duration | 1.14 seconds |
| DQA Stage Duration | 1.31 seconds |
| Analytics Stage Duration | 0.81 seconds |
| Reporting Stage Duration (5 workbooks + ZIP) | 37.80 seconds |
| Peak Memory Allocation (`tracemalloc`) | 374.14 MB |
| Unit Test Suite Status | 111 passed, 0 failed (tests/unit) |

---

## 6. Action Items Identified for Phase F Correction
1. **Fix Date Parsing in `core/cleaning.py`:** Support ISO datetime strings with time components (`^\d{4}-\d{2}-\d{2}(?:[ T].*)?$`) and properly handle numeric Excel serials in DOB to eliminate all 2,141 false-positive DQA exceptions.
2. **Support Case-Insensitive Clinical Vocabulary in `analytics/art.py` and `analytics/prep.py`:** Ensure `"Known Positive"` (case-insensitive) qualifies for `plhiv` and lowercase `'switched'` qualifies for `prep_q1`, bringing Service Summary reconciliation to 100% (0 cell differences).
3. **Implement Full KPI Demographic Sheet in `analytics/demographics.py` and `reporting/`:** Transcribe legacy Cell 84 logic into a dedicated KPI calculator and export layout producing the 24-column grouped header sheet.
