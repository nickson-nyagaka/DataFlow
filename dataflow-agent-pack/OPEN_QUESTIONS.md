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
- **Status:** Resolved
- **Decision:** Omit completely from summary sheets (never computed in legacy notebook; D-029).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/summary_builder.py`, Phase 5.

---

### OQ-12: `TotalCohort` denominator definition
- **Status:** Resolved
- **Decision:** Unique UIC count of all active register rows (`nunique(uic)` in Register sheet), exactly matching legacy notebook cell 66 (D-027).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/summaries.py`, Phase 4.

---

### OQ-13: NSP block header fill color
- **Status:** Resolved
- **Decision:** Keep legacy coral fill (#FF7D81) matching historical workbook styling (D-030).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/excel_exporter.py`, Phase 5.

---

### OQ-14: Identifier masking in report exports
- **Status:** Resolved
- **Decision:** Include full identifiers with confidentiality notice in Run Metadata (required for clinical partner follow-up) (D-031).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/package_builder.py`, `ui/exports.py`, Phase 5/6.

---

### OQ-15: `total_nsp_SEM` in PWID full semester report
- **Status:** Resolved
- **Decision:** Compute as sum of Q1 and Q2 commodity distributions (`total_nsp_q1 + total_nsp_q2`) (D-032).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `analytics/nsp.py`, `reporting/`, Phase 4/5.

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

---

### OQ-24: Reporting Package Bundle Structure and Format
- **Status:** Resolved
- **Decision:** Emit both a master multi-tab Excel workbook and a modular ZIP archive containing separate workbooks (D-033).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/package_builder.py`, Phase 5.

---

### OQ-25: DQA Exceptions Sheet Layout When 0 Exceptions Detected
- **Status:** Resolved
- **Decision:** Retain standard 7-column table headers with an informational banner row ("No data quality exceptions detected. All records passed validation.") (D-034).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/package_builder.py`, `reporting/dqa_exporter.py`, Phase 5.

---

### OQ-26: Cleaned Data Identifier Masking Method in Export
- **Status:** Resolved
- **Decision:** Apply deterministic 8-character salted pseudo-hash `MASK-XXXX` when identifier masking is enabled (D-035).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/package_builder.py`, `reporting/cleaned_data_exporter.py`, Phase 5.

---

### OQ-27: Geography Casing Standard in Exported Summary Rows
- **Status:** Resolved
- **Decision:** Apply Title Case (`Nairobi`, `Sr Name`, `Western`) to county, sr_name, and region in summary tables (D-036).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/summary_builder.py`, `reporting/excel_exporter.py`, Phase 5.

---

### OQ-28: Sorting Order of Summary Data Rows
- **Status:** Resolved
- **Decision:** Apply hierarchical alphabetical sorting `County -> SR Name -> Region`, placing any `(MISSING)` geography rows at the bottom before the TOTAL row (D-037).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/summary_builder.py`, Phase 5.

---

### OQ-29: Summary Indicator Value Types & Formula Verification Precision
- **Status:** Resolved
- **Decision:** All 48 summary indicator columns are strictly non-negative integers; formula validator verifies exact integer equality (`diff == 0`) (D-038).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/workbook_validator.py`, Phase 5.

---

### OQ-30: Inclusion of Age × Sex Disaggregated Pivot Sheet (Cell 84)
- **Status:** Resolved
- **Decision:** Export the Age x Sex Disaggregated Pivot Sheet (Cell 84) as a separate standalone workbook inside the ZIP package, preserving legacy cell 84 disaggregated reporting (D-039).
- **Date decided:** 2026-11-10
- **Affected file/function/column/phase:** `reporting/package_builder.py`, `reporting/excel_exporter.py`, Phase 5.

---

### OQ-31: Multi-Page Navigation Architecture
- **Status:** Resolved
- **Decision:** Modern Streamlit `st.navigation` and `st.Page` API with sidebar page groupings (Workflow, Inspection, Governance) and icons (D-040).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `app.py`, `ui/`, Phase 6.

---

### OQ-32: User Workflow Progression & State Machine Gating
- **Status:** Resolved
- **Decision:** Guided state machine: Upload unlocks Processing; downstream pages (DQA, Analytics, Exports) unlock only after processing completes (D-041).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `app.py`, `ui/`, Phase 6.

---

### OQ-33: Critical DQA Exception Blocking Policy in UI
- **Status:** Resolved
- **Decision:** Block summary/ZIP exports while Critical exceptions exist (DQA workbook and Cleaning Log always downloadable); display banner per Critical rule; multi-field override requiring name and >= 20 char reason per rule tied to file hash and counts; mark overridden outputs PROVISIONAL; support advisory mode; fail closed; append-only audit log in `runtime/audit/` (D-042).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `ui/processing.py`, `ui/data_quality.py`, `ui/exports.py`, `core/override.py`, Phase 6.

---

### OQ-34: Export Download Presentation on Exports Page
- **Status:** Resolved
- **Decision:** Primary button for Master Excel Package (.xlsx) + secondary button for Modular ZIP (.zip) + individual file download buttons (D-043).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `ui/exports.py`, Phase 6.

---

### OQ-35: Session Reset and Temporary Storage Cleanup
- **Status:** Resolved
- **Decision:** 'New Session' action purges session state and deletes all files in `runtime/temporary/` (D-044).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `app.py`, `ui/`, Phase 6.

---

### OQ-36: Windows Deployment Script (`run_dataflow.ps1` & `.bat`) Architecture
- **Status:** Resolved
- **Decision:** Dual launcher: automated `run_dataflow.ps1` with an execution-policy auto-bypass companion `run_dataflow.bat`, verifying python environment and auto-launching browser at `http://127.0.0.1:8501` (D-045).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `run_dataflow.ps1`, `run_dataflow.bat`, Phase 7.

---

### OQ-37: Large-File Performance Stress Testing & Audit Matrix
- **Status:** Resolved
- **Decision:** Progressive, end-to-end stress testing matrix across 10k, 40k, 80k, 120k, and 160k rows × 100-300 columns using realistic Register and KPLHIV workbooks; 3x runs reporting median execution time, peak memory, per-stage timings, analytical accuracy equivalence, memory leaks/copies, and documenting results in `docs/benchmarks/PERFORMANCE_REPORT.md` (D-046).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `scripts/audit/benchmark_stress.py`, `docs/benchmarks/PERFORMANCE_REPORT.md`, Phase 7.

---

### OQ-38: Network Isolation Verification Protocol
- **Status:** Resolved
- **Decision:** Programmatic socket monkeypatching test in `tests/integration/test_network_isolation.py` intercepting all outbound socket/urllib/requests calls during full run + offline `pip-audit` vulnerability review (D-047).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `tests/integration/test_network_isolation.py`, Phase 7.

---

### OQ-39: Field Error Diagnostic & Support Bundle Handling
- **Status:** Resolved
- **Decision:** One-click sanitized Diagnostic Support Bundle export in `runtime/audit/diagnostics/` packaging system specs, environment, config hashes, and scrubbed tracebacks (ZERO PII/UICs) (D-048).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `core/diagnostics.py`, `ui/about.py`, Phase 7.

---

### OQ-40: Provisional Indicators & Unresolved Questions Final Documentation
- **Status:** Resolved
- **Decision:** Dedicated appendix in `docs/reports/PHASE_7_REPORT.md`, dedicated section in `docs/USER_GUIDE.md`, and explicit marking in exported Excel Run Metadata sheet (D-049).
- **Date decided:** 2026-11-11
- **Affected file/function/column/phase:** `docs/reports/PHASE_7_REPORT.md`, `docs/USER_GUIDE.md`, Phase 7.



