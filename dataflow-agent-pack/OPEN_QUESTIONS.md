# OPEN QUESTIONS REGISTER

Maintain sequential IDs (OQ-01, OQ-02, ...).
Status values: Open · Answered · Resolved · Withdrawn.

---

### OQ-01: Is NSP also required in the PLHIV-service pathway for PWID?
- **Status:** Open
- **Why it matters:** Changes Defined Package calculation for KPLHIV PWID clients.
- **Affected file/function/column/phase:** `analytics/defined_package.py`, `config/populations/pwid.yaml`, Phase 4.
- **Options:**
  - A. Yes
  - B. No (until approved definition says otherwise)
  - C. Only for PWID with injecting risk
- **Recommended default:** B. No
- **Blocking:** No (Phase 4)

---

### OQ-02: Which templates use which age categories (notebook cells 57 vs 84 differ)? Should missing age be `Unknown`?
- **Status:** Open
- **Why it matters:** Determines age grouping columns in final Excel summary packages.
- **Affected file/function/column/phase:** `analytics/demographics.py`, `reporting/`, Phase 4/5.
- **Options:**
  - A. List per template, missing age as `Unknown`
  - B. Standardize across all populations
- **Recommended default:** A. List per template, missing age as `Unknown`
- **Blocking:** No (Phase 4)

---

### OQ-03: Missing sex: `Unknown` column in pivots, or excluded with a footnote?
- **Status:** Open
- **Why it matters:** Notebook cell 84 uses `.fillna('F')`. Rule D-003 prohibits defaulting missing sex.
- **Affected file/function/column/phase:** `analytics/demographics.py`, `reporting/`, Phase 4/5.
- **Options:**
  - A. `Unknown` column in pivots
  - B. Excluded from pivot with footnote
- **Recommended default:** A. `Unknown` column
- **Blocking:** No (Phase 4)

---

### OQ-04: Duplicate UIC policy for DQA flagging and indicator aggregation
- **Status:** Resolved
- **Decision:** Flag all rows sharing a duplicate UIC (`keep=False`) in DQA exception report; compute analytical indicators at client grain (`nunique(uic)`). Zero records auto-deleted (D-017).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/deduplication.py`, `core/validation.py`, Phase 3.

---

### OQ-05: Reporting calendar: which visit columns/months belong to Q1 and Q2 in each register template?
- **Status:** Open
- **Why it matters:** Period engine column mappings and semester boundary calculations.
- **Affected file/function/column/phase:** `core/periods.py`, `config/reporting/periods.yaml`, Phase 4.
- **Options:**
  - A. Owner confirms per-population calendar mapping
- **Recommended default:** Standard 3 visits per quarter
- **Blocking:** No (Phase 4)

---

### OQ-06: Intended rule for `hts_sem`: "(Q1 and Q2) or (Q2 and enrolled in/after month M)"
- **Status:** Open
- **Why it matters:** Semester HTS indicator calculation.
- **Affected file/function/column/phase:** `analytics/hts.py`, Phase 4.
- **Options:**
  - A. M = 4 / 7 / 10 configured in reporting cycle
- **Recommended default:** Config per reporting cycle
- **Blocking:** No (Phase 4)

---

### OQ-07: HIV × ART Inconsistency Rule Definition
- **Status:** Resolved
- **Decision:** Split into two separate rules: `DQA_HIV_NEG_ON_ART` (Negative on ART, Critical) and `DQA_HIV_POS_NO_ART` (Known Positive not on ART, Major) (D-014).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/validation.py`, Rule `DQA_HIV_ART`, Phase 3.

---

### OQ-08: Allowed-value vocabulary per categorical field
- **Status:** Resolved
- **Decision:** Normalize known case variants (e.g. `'known positive'` -> `'Known Positive'`); retain unrecognised values untouched in DataFrame for DQA flagging. Zero silent coercion (D-008).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/cleaning.py`, `config/vocabularies/`, Phase 2.

---

### OQ-09: Viral load suppression definition and window
- **Status:** Open
- **Why it matters:** Viral load suppression indicator denominator and LDL interpretation.
- **Affected file/function/column/phase:** `analytics/viral_load.py`, Phase 4.
- **Options:**
  - A. Latest in reporting period, LDL or <200 copies/ml
  - B. Latest in 12 months
- **Recommended default:** A. Latest in period per D-002
- **Blocking:** No (Phase 4)

---

### OQ-10: Active clients definition across KPLHIV and Register
- **Status:** Open
- **Why it matters:** Reconciles monthly active columns vs ART outcome status.
- **Affected file/function/column/phase:** `analytics/kplhiv.py`, Phase 4.
- **Options:**
  - A. Owner confirms applicable month columns per cycle
- **Recommended default:** Monthly active columns matching period
- **Blocking:** No (Phase 4)

---

### OQ-11: `OLD_Cohort` and `NEW_Cohort` columns
- **Status:** Open
- **Why it matters:** Referenced in legacy column order but never computed.
- **Affected file/function/column/phase:** `reporting/summary_builder.py`, Phase 5.
- **Options:**
  - A. Remove unless defined by Owner
  - B. Compute based on enrolment date before vs during period
- **Recommended default:** A. Remove unless defined
- **Blocking:** No (Phase 5)

---

### OQ-12: `TotalCohort` denominator definition
- **Status:** Open
- **Why it matters:** Denominator across summary indicators.
- **Affected file/function/column/phase:** `analytics/summaries.py`, Phase 4.
- **Options:**
  - A. Unique UIC count of all active register rows
  - B. Only clients with activity or enrolment in reporting period
- **Recommended default:** A. Unique UIC count of all register rows
- **Blocking:** No (Phase 4)

---

### OQ-13: NSP block header fill color
- **Status:** Open
- **Why it matters:** Styling of Excel summary package for PWID.
- **Affected file/function/column/phase:** `reporting/excel_exporter.py`, Phase 5.
- **Options:**
  - A. Keep coral fallback (`FF7D81`)
  - B. Assign new hex color
- **Recommended default:** A. Keep coral fallback (`FF7D81`)
- **Blocking:** No (Phase 5)

---

### OQ-14: Identifier masking in report exports
- **Status:** Open
- **Why it matters:** Client privacy vs operational utility for Sub-Recipients.
- **Affected file/function/column/phase:** `reporting/package_builder.py`, `ui/exports.py`, Phase 5/6.
- **Options:**
  - A. UICs visible by default, UI prominent warning and optional masking checkbox
  - B. Masked by default
- **Recommended default:** A. UICs visible with warning and optional masking
- **Blocking:** No (Phase 5/6)

---

### OQ-15: `total_nsp_SEM` in PWID full semester report
- **Status:** Open
- **Why it matters:** Export block lists `total_nsp_SEM` but notebook code omitted the sum.
- **Affected file/function/column/phase:** `analytics/nsp.py`, `reporting/`, Phase 4/5.
- **Options:**
  - A. Compute as `total_nsp_Q1 + total_nsp_Q2`
  - B. Omit column
- **Recommended default:** A. Compute sum
- **Blocking:** No (Phase 4/5)

---

### OQ-16: Records with missing Sub-Recipient (`sr_name`)
- **Status:** Resolved
- **Decision:** Retain record, assign `sr_name = 'Unknown'`, flag Critical DQA exception in Phase 3. Zero rows dropped during ingestion (D-009).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/cleaning.py`, `core/audit.py`, `core/validation.py`, Phase 2/3.

---

### OQ-17: TB Diagnosed Without Screening Criteria
- **Status:** Resolved
- **Decision:** Flag any TB diagnosis where screening is NOT documented as 'Yes' (missing/NaN or explicitly 'No') (D-015).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/validation.py`, Rule `DQA_TB_UNSCREENED`, Phase 3.

---

### OQ-18: Handling completely blank rows in raw sheets
- **Status:** Resolved
- **Decision:** Count in `rows_in`, drop 100% empty rows, record in audit trail as `dropped_empty_rows` (`rows_in == rows_out + dropped_empty_rows`) (D-010).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/ingestion.py`, `core/audit.py`, Phase 2.

---

### OQ-19: Date parsing format convention
- **Status:** Resolved
- **Decision:** Day-First (`DD/MM/YYYY`, `dayfirst=True`) with ISO-8601 and Excel numeric serial date fallbacks; unparseable strings become `NaT` and flag for DQA (D-011).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/ingestion.py`, `core/cleaning.py`, Phase 2.

---

### OQ-20: Missing required workbook sheets
- **Status:** Resolved
- **Decision:** Raise structured `IngestionError` naming missing sheet (`Register` or `KPLHIV`) and halt early (D-012).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/ingestion.py`, Phase 2.

---

### OQ-21: STI Diagnosed Without Screening Criteria
- **Status:** Resolved
- **Decision:** Flag any STI diagnosis where screening is NOT documented as 'Yes' (missing/NaN or explicitly 'No') (D-016).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/validation.py`, Rule `DQA_STI_UNSCREENED`, Phase 3.

---

### OQ-22: Cross-sheet CCC Reconciliation Severity (Register vs KPLHIV)
- **Status:** Resolved
- **Decision:** Register CCC missing in KPLHIV is `Critical`; KPLHIV CCC missing in Register is `Major` (D-018).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/validation.py`, Rules `DQA_CCC_REG_NOT_KPLHIV` and `DQA_CCC_KPLHIV_NOT_REG`, Phase 3.

---

### OQ-23: Rule Registry Severity Classification & `block_on_critical` Policy
- **Status:** Resolved
- **Decision:** Approve proposed classification (Critical: missing/duplicate UIC, HIVxART, HIVxPrEP, missing county/SR; Major: unscreened TB/STI, missing demographics, CCC Register not in KPLHIV; Minor: KPLHIV not in Register, unparseable dates). Set `block_on_critical: true` by default (D-019).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `config/settings.yaml`, `core/validation.py`, Phase 3.
