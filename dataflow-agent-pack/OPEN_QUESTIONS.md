# OPEN QUESTIONS REGISTER

Maintain sequential IDs (OQ-01, OQ-02, ...).
Status values: Open · Answered · Resolved · Withdrawn.

---

### OQ-01: Is NSP also required in the PLHIV-service pathway for PWID?
- **Status:** Resolved
- **Decision:** Require NSP in both the general Defined Package pathway and the PLHIV-service pathway for PWID (`require_nsp: true`). FSW, MSM, TG, VP do not require NSP (D-020).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/defined_package.py`, `config/populations/pwid.yaml`, Phase 4.

---

### OQ-02: Which templates use which age categories (notebook cells 57 vs 84 differ)? Should missing age be `Unknown`?
- **Status:** Resolved
- **Decision:** Standard 4-tier age bands (`Below 15`, `15-19`, `20-24`, `25+`). Missing ages are classified as `'Unknown'` and flagged in DQA (never defaulted) (D-021).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/demographics.py`, `reporting/`, Phase 4.

---

### OQ-03: Missing sex: `Unknown` column in pivots, or excluded with a footnote?
- **Status:** Resolved
- **Decision:** Exclude records with missing sex from sex-disaggregated breakdowns and report an explicit footnote `(Missing Sex: N)` (never defaulting to 'F') (D-022).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/demographics.py`, `reporting/`, Phase 4.

---

### OQ-04: Duplicate UIC policy for DQA flagging and indicator aggregation
- **Status:** Resolved
- **Decision:** Flag all rows sharing a duplicate UIC (`keep=False`) in DQA exception report; compute analytical indicators at client grain (`nunique(uic)`). Zero records auto-deleted (D-017).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/deduplication.py`, `core/validation.py`, Phase 3.

---

### OQ-05: Reporting calendar: which visit columns/months belong to Q1 and Q2 in each register template?
- **Status:** Resolved
- **Decision:** Exactly 3 visits per quarter across all 5 populations (Visits 1-3 = Q1, Visits 4-6 = Q2, Visits 1-6 = SEM), driven by explicit mapping in `periods.yaml` (D-023).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `core/periods.py`, `config/reporting/periods.yaml`, Phase 4.

---

### OQ-06: Intended rule for `hts_sem`: "(Q1 and Q2) or (Q2 and enrolled in/after month M)"
- **Status:** Resolved
- **Decision:** Any test in semester: tested in Q1 OR tested in Q2 (`hts_q1 == 1 | hts_q2 == 1`) (D-024).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/hts.py`, Phase 4.

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
- **Status:** Resolved
- **Decision:** Suppression rate denominator is KPLHIV clients with a documented valid VL result; `>LDL` is unparseable and flagged for DQA; suppression defined as `LDL`, `<LDL`, or numeric < 200 copies/ml (D-025).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/viral_load.py`, Phase 4.

---

### OQ-10: Active clients definition across KPLHIV and Register
- **Status:** Resolved
- **Decision:** Count of all registered KPLHIV clients (`nunique(uic)` in KPLHIV sheet), exactly matching legacy notebook cell 66 (D-026).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/kplhiv.py`, Phase 4.

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
- **Status:** Resolved
- **Decision:** Unique UIC count of all active register rows (`nunique(uic)` in Register sheet), exactly matching legacy notebook cell 66 (D-027).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/summaries.py`, Phase 4.

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
