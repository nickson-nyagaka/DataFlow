# KNOWN ISSUES & AUDIT FINDINGS — DATAFLOW

Comprehensive defect catalog, audit findings, and legacy quirk evidence extracted from `reference/OPTIMIZED_DATA_MGT.sanitized.ipynb`.
Audit date: 2026-11-10 | Author: DATAFLOW Engineering Agent | Phase: 0

---

## 1. Pre-Audited Leads (L-01 through L-17)

Every lead from Master Brief §5 has been verified programmatically against the executable notebook code.

| Lead ID | Cell Ref | Verdict | Severity | Brief Description |
|---|---|---|---|---|
| **L-01** | Cell 46 | **VERIFIED** | CRITICAL | KPLHIV overwritten by Register data when `s_n` exists |
| **L-02** | Cell 38 | **VERIFIED** | MAJOR | Rule vs comment mismatch (Negative on ART vs Positive on ART) |
| **L-03** | Cells 17, 61, 66 | **VERIFIED** | CRITICAL | UIC duplicates listed but kept; row-propagated flags summed while cohort uses nunique |
| **L-04** | Cells 14, 61 | **VERIFIED** | MAJOR | `.map(capitalize)` mutates strings; inconsistent casing in comparisons |
| **L-05** | Cells 57, 84 | **VERIFIED** | MAJOR | Missing age lands in 'Below 15' in Cell 57, but 'Unknown' in Cell 84 |
| **L-06** | Cell 84 | **VERIFIED** | MAJOR | Missing sex silently defaulted to Female via `.fillna('F')` |
| **L-07** | Cells 36, 38, 61 | **VERIFIED** | CRITICAL | Positional column slicing (`[:3]`, `[3:6]`) after lexicographic sort (`_10` before `_2`) |
| **L-08** | Cell 54 | **VERIFIED** | MAJOR | Suppressed sums rows while Total_KPLHIV counts unique UICs; unparseable VL unsuppressed |
| **L-09** | Cells 66, 67, 72 | **VERIFIED** | CRITICAL | `groupby` silently drops rows with NaN keys; title-case vs upper-case merge key mismatches |
| **L-10** | Cell 61 | **VERIFIED** | MAJOR | `hts_sem` uses `month >= 7` while comment states `month >= 10`; ignores enrolment year |
| **L-11** | Cell 69 | **VERIFIED** | MINOR | `OLD_Cohort` and `NEW_Cohort` referenced in ordering but never computed |
| **L-12** | Cells 01, 04, 61 | **VERIFIED** | MAJOR | Hardcoded calendar assumptions, Windows path (`F:\...`), fixed `skiprows=2` |
| **L-13** | Cells 75, 77, 80, 82 | **VERIFIED** | MAJOR | Four copy-pasted exporters with ~90% duplicate openpyxl code |
| **L-14** | Cell 14 | **VERIFIED** | MAJOR | `.map(...)` called elementwise over entire DataFrame; catastrophic performance |
| **L-15** | Cell 61 | **VERIFIED** | MAJOR | Semester aggregation logic is non-uniform across indicators |
| **L-16** | Cell 52 | **VERIFIED** | MAJOR | One-way CCC check only (KPLHIV -> Register); null left IDs uncounted |
| **L-17** | Cell 61 | **VERIFIED** | CRITICAL | NSP requirements commented out of Defined Package for all populations |

---

### Detailed Lead Verification & Evidence

#### L-01: KPLHIV Overwritten by Register Data
- **Cell:** 46
- **Verdict:** `VERIFIED`
- **Severity:** `CRITICAL`
- **Code Evidence:**
  ```python
  if 's_n' in ConsolidatedFSW.columns:
      ConsolidatedKPLHIV = ConsolidatedFSW.drop(columns=['s_n'])
  ```
- **Technical Analysis:** If the Register contains a serial number column `s_n`, the variable `ConsolidatedKPLHIV` is completely reassigned to `ConsolidatedFSW` (Register data). All subsequent KPLHIV and viral-load calculations operate on Register data instead of the true KPLHIV sheet.
- **Planned Resolution:** `BUG-FIX`. Ingest sheets into separate, strongly typed immutable data structures.

#### L-02: Rule vs Comment Mismatch (HIV × ART Check)
- **Cell:** 38
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  #check those who tested Positive and currently on art services
  for h_col, a_col in zip(hiv_cols, art_cols):
      condition |= ConsolidatedFSW[h_col].isin(['Negative']) & ConsolidatedFSW[a_col].eq('Yes')
  ConsolidatedFSW['NegativeART'] = np.where(condition, 1, 0)
  ```
- **Technical Analysis:** The comment describes finding positive clients receiving ART, but the executable condition tests `Negative` HIV with `Yes` ART and creates `NegativeART`.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE` / DQA Rule Registry. Split into two explicit DQA rules per OQ-07: Rule DQA-007A (Negative on ART) and Rule DQA-007B (Positive not on ART).

#### L-03: Duplicates Listed But Kept; Numerators Exceed Cohort
- **Cells:** 17, 61, 66
- **Verdict:** `VERIFIED`
- **Severity:** `CRITICAL`
- **Code Evidence:**
  ```python
  # Cell 17: fsw_dups = ConsolidatedFSW[ConsolidatedFSW.duplicated(subset=['kp_vp_unique_identifier_code'])]
  # Cell 61: has_by_id = row_has.groupby(df[id_col]).transform("max")
  # Cell 66: TotalCohort=('kp_vp_unique_identifier_code', 'nunique'), HTSQ1=('hts_q1', 'sum')
  ```
- **Technical Analysis:** Duplicate UICs are displayed in Cell 17 but never removed. In Cell 61, `any_in_unique_allrows` propagates event flags to all rows of a duplicate UIC. In Cell 66, indicator flags are aggregated with `'sum'` (row sum), while `TotalCohort` aggregates with `'nunique'`. A client with 3 duplicate rows and a positive test flag contributes 3 to the indicator numerator and 1 to `TotalCohort`.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE` (BR-005 / D-004 / OQ-04). Flag duplicate UICs as Critical DQA exceptions; calculate client-grain indicators using `nunique(uic where flag)` so numerators can never exceed cohort size.

#### L-04: String Normalization and Vocabulary Casing
- **Cells:** 14, 61
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  # Cell 14: ConsolidatedKPLHIV = ConsolidatedKPLHIV.map(lambda x: str(x).capitalize() if isinstance(x, str) else x)
  # Cell 61 (line 196): ConsolidatedFSW['plhiv'] = np.where(any_in_unique_allrows(ConsolidatedFSW, hiv_q1_cols, ['Known positive']), 1, 0)
  # Cell 36: ConsolidatedFSW[h_col].isin(['Positive', 'Known Positive'])
  ```
- **Technical Analysis:** Element-wise `.capitalize()` converts `"Known Positive"` into `"Known positive"`. Cell 61 tests for `"Known positive"` (lowercase p), whereas Cell 36 tests for `"Known Positive"` (uppercase P).
- **Planned Resolution:** `BUG-FIX`. Replace free-form string capitalization with typed vocabulary maps in `config/vocabularies/*.yaml` that canonicalize case variants safely.

#### L-05: Missing Age Landed in 'Below 15'
- **Cells:** 57, 84
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  # Cell 57: ConsolidatedFSW['age_group'] = ConsolidatedFSW['age'].apply(
  #     lambda x: '15-19' if 15 <= x <= 19 else ('20-24' if 20 <= x <= 24 else ('25+' if x >= 25 else 'Below 15')))
  # Cell 84: def assign_age_group(age): if pd.isna(age): return 'Unknown' ...
  ```
- **Technical Analysis:** In Cell 57, when `age` is `NaN`, all range comparisons evaluate to `False`, falling through to `'Below 15'`. In Cell 84, `pd.isna(age)` returns `'Unknown'`.
- **Planned Resolution:** `BUG-FIX` (BR-006 / OQ-02). Missing age is categorized as `'Unknown'`, never `'Below 15'`.

#### L-06: Sex Imputed to Female
- **Cell:** 84
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  kvp_merged['sex_group'] = (
      kvp_merged['sex_m_f_'].astype('string').str.strip().str.upper().replace({'MALE': 'M', 'FEMALE': 'F'}).fillna('F')
  )
  ```
- **Technical Analysis:** Missing sex values are silently replaced with `'F'` (Female) via `.fillna('F')` in the disaggregated pivot export.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE` (BR-004 / D-003). Never impute sex; report missing sex as `'Unknown'`.

#### L-07: Lexicographical Sorting & Positional Slicing
- **Cells:** 36, 38, 42, 61
- **Verdict:** `VERIFIED`
- **Severity:** `CRITICAL`
- **Code Evidence:**
  ```python
  # Cell 61: prep_cols = sorted(prep_cols); prep_q1_cols = prep_cols[:3]; prep_q2_cols = prep_cols[3:6]
  # Cell 38: for h_col, a_col in zip(hiv_cols, art_cols): ...
  ```
- **Technical Analysis:** Python standard `sorted()` orders strings lexicographically: `['col_1', 'col_10', 'col_2']`. Positional slicing `[:3]` captures visits 1, 10, and 2 instead of 1, 2, and 3. In Cell 38, `zip()` pairs columns based on alphabetical sort order without validating date alignment.
- **Planned Resolution:** `BUG-FIX` (BR-007). Explicit column-to-period mapping in `config/reporting/periods.yaml` with pre-calculation validation.

#### L-08: Viral Load Aggregation Mismatch
- **Cell:** 54
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  summary_KPLHIV = ConsolidatedKPLHIV.groupby(['county', 'sr_name', 'region']).agg(
      Total_KPLHIV=('kp_vp_unique_identifier_code_', 'nunique'),
      Suppressed=('is_suppressed','sum')
  )
  ```
- **Technical Analysis:** `Suppressed` sums rows where `is_suppressed` is true, while `Total_KPLHIV` counts unique clients. A client with multiple VL records is counted multiple times in `Suppressed`. Any unparseable string returns `"UNKNOWN"` and is treated as unsuppressed.
- **Planned Resolution:** `BUG-FIX` / `BUSINESS-RULE-CHANGE` (BR-003 / D-002 / OQ-09). Use client grain for suppression based on the latest valid result in the reporting period.

#### L-09: Groupby Drops Missing Keys; Join Key Mismatches
- **Cells:** 66, 67, 72
- **Verdict:** `VERIFIED`
- **Severity:** `CRITICAL`
- **Code Evidence:**
  ```python
  # Cell 66: ConsolidatedFSW.groupby(['county', 'sr_name', 'region'])
  # Cell 67: df['county'] = df['county'].astype(str).str.strip().str.title()
  # Cell 73: df[col] = df[col].astype(str).str.strip().str.upper()
  ```
- **Technical Analysis:** Standard `groupby` drops rows where any grouping key is `NaN`, causing silent loss of client counts. Furthermore, keys flip between uppercase and title-case, causing left joins to fail silently and produce `NaN` indicators. `astype(str)` converts `NaN` into `'nan'`.
- **Planned Resolution:** `BUG-FIX`. Use `dropna=False` in groupbys; represent missing geography explicitly as `"(MISSING)"`; enforce uniform case normalisation across all frames.

#### L-10: `hts_sem` Month Threshold Discrepancy
- **Cell:** 61
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  # boolean: enrolled in Apr or later (month >= 10)
  enrolled_Apr_plus = ConsolidatedFSW['date_of_enrolment'].dt.month >= 7
  ```
- **Technical Analysis:** The comment specifies April or later (which in PEPFAR Q3 corresponds to month 10 in a Jul–Jun fiscal year or month 4 in calendar year), but the executable code evaluates `month >= 7` (July). The enrolment year is ignored.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE` / Config (OQ-06). Define the exact semester HTS qualification rule in configuration.

#### L-11: Uncomputed Cohort Columns
- **Cell:** 69
- **Verdict:** `VERIFIED`
- **Severity:** `MINOR`
- **Code Evidence:**
  ```python
  cohort_cols = ['OLD_Cohort', 'NEW_Cohort', 'TotalCohort']
  base_order = keys + age_group_cols + cohort_cols + remaining
  # new_order filtered: [c for c in new_order if c in final_summary_FSW.columns]
  ```
- **Technical Analysis:** Columns `OLD_Cohort` and `NEW_Cohort` are included in the desired ordering list, but are never calculated anywhere in the notebook, so they are silently omitted.
- **Planned Resolution:** `TECHNICAL` (OQ-11). Define calculation rules or remove from configuration.

#### L-12: Hardcoded Assumptions & Absolute Paths
- **Cells:** 01, 04, 48, 61
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  directory = r"F:\.shortcut-targets-by-idITOlPBpvV43hPTKn0MJkDV-Yj1aswrk5\DATA MANAGEMENT\..."
  month_cols = ['jul', 'aug', 'sep', 'oct', 'nov', 'dec']
  ```
- **Technical Analysis:** The script hardcodes Windows absolute paths, fixed month strings, and fixed `skiprows=2`.
- **Planned Resolution:** `TECHNICAL`. Use `pathlib`, configurable input paths, and dynamic period mappings.

#### L-13: Duplicate Exporter Code
- **Cells:** 75, 77, 80, 82
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:** 4 separate functions totaling 1,479 lines of near-identical openpyxl formatting code.
- **Technical Analysis:** High maintenance overhead and bug propagation risk (e.g. `total_nsp_SEM` bug).
- **Planned Resolution:** `TECHNICAL`. Single parametrised exporter in `reporting/excel_exporter.py`.

#### L-14: Elementwise `.map(...)` Performance Bottleneck
- **Cell:** 14
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  ConsolidatedKPLHIV = ConsolidatedKPLHIV.map(lambda x: str(x).capitalize() if isinstance(x, str) else x)
  ConsolidatedKPLHIV = ConsolidatedKPLHIV.map(lambda x: x.strip() if isinstance(x, str) else x)
  ```
- **Technical Analysis:** Running two full-frame `.map()` operations across an 80k×300 frame executes ~48 million Python function calls, blocking execution for minutes.
- **Planned Resolution:** `TECHNICAL`. Vectorized column operations targeted strictly to string columns.

#### L-15: Non-Uniform Semester Logic
- **Cell:** 61
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  - PrEP / STI / TB / Condoms / DefinedPackage: `(Q1 + Q2) >= 1` (union).
  - HTS: `((Q1 > 0) & (Q2 > 0)) | ((Q2 > 0) & (month >= 7))` (intersection / threshold).
  - New on ART: No semester indicator computed.
- **Technical Analysis:** Indicators cannot be aggregated into semester figures using a single generic rule.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE`. Explicit indicator-by-indicator period logic documented in `docs/INDICATOR_DICTIONARY.md`.

#### L-16: One-Directional CCC Number Check
- **Cell:** 52
- **Verdict:** `VERIFIED`
- **Severity:** `MAJOR`
- **Code Evidence:**
  ```python
  right_ids = set(right_ser.unique())
  left_norm = _normalize_ids(ConsolidatedKPLHIV[left_key])
  # Checks only if KPLHIV CCC numbers are in Register; never checks Register -> KPLHIV
  ```
- **Technical Analysis:** The check detects KPLHIV clients missing from Register, but fails to detect Register clients with CCC numbers missing from KPLHIV.
- **Planned Resolution:** `BUG-FIX` / DQA Engine. Bidirectional CCC/NUPI validation in Phase 3.

#### L-17: NSP Commented Out of Defined Package
- **Cell:** 61
- **Verdict:** `VERIFIED`
- **Severity:** `CRITICAL`
- **Code Evidence:**
  ```python
  # Lines 206, 216: # (ConsolidatedFSW['nsp_q1'] == 1) &
  # Lines 229, 240: #  (ConsolidatedFSW['nsp_q1'] == 1) &
  ```
- **Technical Analysis:** NSP distribution is commented out in both Defined Package pathways for all populations, including PWID.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE` (BR-001 / D-001). Mandate NSP for PWID in general pathway via YAML configuration.

---

## 2. New Audit Findings (NI-01 through NI-07)

During the cell-by-cell execution audit, the following additional defects and risks were discovered:

### NI-01: `total_nsp_SEM` Silently Omitted in Exporter
- **Cell:** 82 (lines 214, 281)
- **Severity:** `MAJOR`
- **Code Evidence:**
  `Block: 'NSP' -> [..., ('SEM', 'total_nsp_SEM')]`, but `total_nsp_SEM` is **never aggregated or computed** in `build_summary_fsw` or Cell 66.
- **Impact:** The column filtering step silently drops `total_nsp_SEM` from the PWID Full Semester Excel export.
- **Planned Resolution:** `BUG-FIX`. Compute `total_nsp_SEM = total_nsp_Q1 + total_nsp_Q2` in analytics engine.

### NI-02: Silent Row Dropping in FSW Cleaning
- **Cell:** 18
- **Severity:** `MAJOR`
- **Code Evidence:**
  `ConsolidatedFSW = ConsolidatedFSW[ConsolidatedFSW['sr_name'].notna()]`
- **Impact:** Any record with a missing Sub-Recipient name is permanently deleted without an audit trail or DQA exception entry. This filter only exists in the FSW loader, not other populations.
- **Planned Resolution:** `BUSINESS-RULE-CHANGE` (BR-005). Never drop rows silently; keep records and raise a Critical DQA exception for missing SR name.

### NI-03: Casing Inconsistency in PrEP × HIV DQA Check
- **Cell:** 36
- **Severity:** `MAJOR`
- **Code Evidence:**
  `ConsolidatedFSW[h_col].isin(['Positive', 'Known Positive'])`
- **Impact:** If string cleaning was executed, `"Known Positive"` was converted to `"Known positive"` (lowercase p). The check in Cell 36 tests for uppercase `"Known Positive"`, silently failing to flag positive clients receiving PrEP.
- **Planned Resolution:** `BUG-FIX`. Case-insensitive vocabulary matching.

### NI-04: TB DQA Rule Masks Missing Screenings
- **Cell:** 40
- **Severity:** `MINOR`
- **Code Evidence:**
  `screened_no = ConsolidatedFSW[screened_cols].eq('No').all(axis=1)`
- **Impact:** Only rows explicitly containing `'No'` in all screening columns are checked. Clients with `NaN`, blank, or `'NA'` screening values who are diagnosed with TB are not flagged.
- **Planned Resolution:** `BUG-FIX`. Flag any record where diagnosis is `'Yes'` and screening is not `'Yes'`.

### NI-05: Hardcoded Reporting Period Months in Active Check
- **Cell:** 48
- **Severity:** `MAJOR`
- **Code Evidence:**
  `month_cols = ['jul', 'aug', 'sep', 'oct', 'nov', 'dec']`
- **Impact:** The active client check in KPLHIV is hardcoded to July–December. Running the notebook on a January–June reporting cycle produces empty tables or errors.
- **Planned Resolution:** `TECHNICAL`. Dynamic period configuration via `periods.yaml`.

### NI-06: Unconstrained Regex in Register Active Check
- **Cell:** 50
- **Severity:** `MINOR`
- **Code Evidence:**
  `art_outcome_cols = [col for col in ConsolidatedFSW.columns if re.match(r'^art_outcome(_\d+)?$', col)]`
- **Impact:** Matches any column starting with `art_outcome`, potentially aggregating columns outside the active reporting cycle.
- **Planned Resolution:** `TECHNICAL`. Explicit column mapping.

### NI-07: One-Way CCC Check with Hardcoded Threshold
- **Cell:** 52
- **Severity:** `MAJOR`
- **Code Evidence:**
  `SET_THRESHOLD = 500_000` and `right_ids = set(right_ser.unique())`
- **Impact:** Evaluates KPLHIV -> Register only. If Register has 200 clients marked CCC positive who do not exist in KPLHIV, zero exceptions are raised.
- **Planned Resolution:** `BUG-FIX`. Implement bidirectional cross-sheet reconciliation.
