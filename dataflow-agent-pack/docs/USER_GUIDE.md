# DATAFLOW v1.0.0 — User Guide & Operational Handbook

---

## 1. Quick Reference Card (One-Page Field Cheatsheet)

```
========================================================================================
                               DATAFLOW QUICK REFERENCE CARD
========================================================================================

1. LAUNCH APPLICATION
   - Double-click 'run_dataflow.bat' in the project folder.
   - The launcher prepares your environment and opens http://127.0.0.1:8501 in your browser.

2. UPLOAD COHORT DATA
   - Navigate to 'Upload Data' on the sidebar.
   - Select Target Population: FSW | MSM | PWID | TG | VP.
   - Select Reporting Period: Semester (SEM) | Quarter 1 (Q1) | Quarter 2 (Q2).
   - Drag and drop your cohort workbook (.xlsx, .xlsm, .xlsb, or .csv).

3. REVIEW DATA QUALITY (DQA)
   - Critical Severity: Blocks export until fixed or overridden with a Supervisor Token.
   - Major Severity: Highlights clinical inconsistencies (e.g. STI/TB diagnosis without screening).
   - Minor Severity: Highlights formatting anomalies (e.g. float IDs, whitespace).

4. SUPERVISORY OVERRIDES
   - Enter Supervisor Authorization Token to grant an audited exemption for Critical defects.
   - All overrides record supervisor identity, timestamp, and justification in the Run Metadata.

5. EXPORT & DOWNLOAD
   - Master Workbook: All-in-one spreadsheet containing Summary, Cleaned Data, DQA, and Metadata.
   - Modular ZIP: Individual spreadsheets ready for Sub-Recipient submission.
   - Privacy Mode: Check 'Mask Sensitive Identifiers' to apply salted hashes (MASK-XXXX).

6. SUPPORT & TROUBLESHOOTING
   - Go to 'About' tab -> Click 'Generate Diagnostic Support Bundle'.
   - Produces a sanitized, zero-PII zip archive to share with technical support.
========================================================================================
```

---

## 2. Step-by-Step Workflow Guide

### Step 1: Launching the System
- Ensure Python 3.11+ is installed.
- Double-click **`run_dataflow.bat`** on your desktop or project folder.
- If using PowerShell directly, run:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\run_dataflow.ps1
  ```
- Your default web browser will open to `http://127.0.0.1:8501`.

### Step 2: Dashboard Overview
- The **Dashboard** provides high-level visibility into your most recent pipeline run.
- Key summary metrics displayed:
  - Total Active Cohort Volume
  - Active KPLHIV (Clients living with HIV on ART)
  - Data Quality Exceptions count (by Critical, Major, Minor severity)
  - HTS Testing Continuum and PrEP Cascade overview
- If no previous run has occurred, the dashboard displays instructions to upload data.

### Step 3: Uploading Cohort Data
1. Click **Upload Data** in the left navigation sidebar.
2. Select your **Target Population**:
   - `FSW`: Female Sex Workers
   - `MSM`: Men who have Sex with Men
   - `PWID`: People Who Inject Drugs (includes Needle & Syringe Program cascade)
   - `TG`: Transgender Individuals
   - `VP`: Vulnerable Populations
3. Select your **Reporting Period**:
   - `SEM`: Full 6-Month Semester (standard bi-annual national reporting)
   - `Q1`: First Quarter (Months 1–3)
   - `Q2`: Second Quarter (Months 4–6)
4. Upload your workbook:
   - Supports `.xlsx`, `.xlsm`, `.xlsb`, and `.csv`.
   - File size up to 200 MB supported.
   - The engine automatically scans sheets (e.g., `Register`, `MSM`, `KPLHIV`) and header rows.

### Step 4: Pipeline Execution & Monitoring
- Once uploaded, click **Execute Pipeline**.
- The **Processing** page displays live status chips with millisecond-accurate stage timers:
  - **Stage 1: Ingestion & Column Normalisation:** Resolves messy aliases and verifies required columns.
  - **Stage 2: Demographic & Clinical Cleaning:** Normalises whitespace, case, and dates.
  - **Stage 3: Data Quality Assurance (DQA):** Executes 12 validation rules across all records.
  - **Stage 4: Analytical Indicator Engine:** Computes 88 indicator columns across cascade cascades.
  - **Stage 5: Reporting Package Generation:** Generates openpyxl workbooks and formulas.

### Step 5: Data Quality Review & Exception Handling
- Click **Data Quality** in the sidebar.
- Filter exceptions by severity:
  - **Critical:** Contradictory clinical records (e.g., Negative client on ART, or Positive not on ART).
  - **Major:** Clinical protocol violations (e.g., Diagnosed with STI without screening record).
  - **Minor:** Typographical defects or formatting quirks (e.g., float-formatted UICs).
- Click **Download DQA Exceptions Workbook** to send line-list corrections back to field clinicians.

### Step 6: Applying Supervisory Overrides
- When Critical DQA exceptions represent valid real-world clinical exceptions (e.g., a transferred client receiving transitional care), an authorized M&E Supervisor can approve an override.
- Enter the **Supervisor Token** (default: `DATAFLOW-SUPERVISOR-SECRET-TOKEN`).
- Select the DQA Rule to exempt and provide an operational justification (e.g., *"Verified with clinic register CCC#12345: transitional ART refill prior to transfer-in"*).
- Click **Apply Override**. An immutable audit record is saved in `runtime/audit/overrides/override_log.json` and embedded into the **Run Metadata** tab of the final report.

### Step 7: Analytics Cascades
- Inspect pre-computed interactive charts:
  - **HTS Testing Cascade:** Tested $\rightarrow$ Negative $\rightarrow$ Positive $\rightarrow$ Linked to ART.
  - **PrEP Continuum:** Screened $\rightarrow$ Eligible $\rightarrow$ Initiated (New) $\rightarrow$ Refill.
  - **Commodities & Services:** Condom distribution, Needle & Syringe Program (NSP) numbers (PWID only), Peer Education coverage.
  - **Demographic Disaggregations:** Age groups (`Below 15`, `15-19`, `20-24`, `25+`, `(MISSING)`) and Sex pivots.

### Step 8: Exporting Reports & Packages
- Click **Export Reports** in the sidebar.
- **Privacy Setting:** If sharing data with external analysts or non-clinical partners, toggle **"Mask Sensitive Identifiers"**. All UICs, CCCs, and NUPIs will be replaced with deterministic 8-character salted pseudo-hashes (`MASK-XXXX`).
- Download options:
  - **Consolidated Master Workbook (`DATAFLOW_Master_<POP>_<PERIOD>.xlsx`):** Contains Summary, Cleaned Register, Cleaned KPLHIV, DQA Exceptions, Run Metadata, and Cleaning Log.
  - **Summary Only Workbook (`01_Summary_<POP>_<PERIOD>.xlsx`):** Pixel-perfect match for national templates with dynamic `=SUM()` Excel formulas.
  - **Cleaned Data Workbook (`02_Cleaned_Data_<POP>.xlsx`):** Streaming export of cleaned cohort records with all 88 calculated indicator columns.
  - **DQA Exceptions Workbook (`03_DQA_Exceptions_<POP>.xlsx`):** Actionable line-list for Sub-Recipient follow-up.
  - **Age × Sex Disaggregation (`04_Age_Sex_Disaggregation_<POP>.xlsx`):** Standalone demographic pivot table.
  - **Complete ZIP Package (`DATAFLOW_Package_<POP>_<PERIOD>.zip`):** Single archive containing all 5 workbooks.

---

## 3. Data Quality Assurance (DQA) Remediation Handbook

| Rule ID | Rule Name | Severity | Defect Condition | Field Remediation Action |
| :--- | :--- | :--- | :--- | :--- |
| **DQA-001** | Duplicate UIC Encounter | Critical | Same UIC appears multiple times in register with conflicting demographic data. | Verify client identity in primary clinic file; merge duplicate rows into a single longitudinal client record. |
| **DQA-002** | Negative Client on ART | Critical | Client recorded as HIV-Negative at encounter but marked as currently on ART (`Yes`). | Confirm HIV status with HTS lab register. If positive, update baseline HIV status to 'Positive' and record CCC number. If negative, remove erroneous ART flag. |
| **DQA-003** | Positive Client Not on ART | Critical | Client recorded as Known Positive or newly tested Positive but marked ART = `No`. | Urgent clinical linkage required. Trace client immediately for rapid ART initiation per national guidelines. |
| **DQA-004** | PrEP in Known Positive | Critical | HIV-positive client recorded as initiating or receiving PrEP refills. | Discontinue PrEP immediately; ensure client is enrolled in ART comprehensive care and viral load monitoring. |
| **DQA-005** | TB Diagnosed Without Screening | Major | Client marked as diagnosed with TB (`Yes`) but TB screening is recorded as `No` or missing. | Update clinical encounter card to record the symptom screening results that preceded the clinical TB diagnosis. |
| **DQA-006** | STI Diagnosed Without Screening | Major | Client marked as diagnosed or treated for STI without prior screening recorded. | Cross-check clinical notes; record physical examination/syndromic screening entry in register. |
| **DQA-007** | Missing Demographics | Major | Client has blank or unrecorded Age, Sex, County, or Sub-Recipient name. | Extract missing demographic information from client's physical intake registration form. |
| **DQA-008** | Invalid Date Sequence | Major | Date of Enrolment is in the future, or occurs before recorded Date of Birth. | Audit client file to correct typographical errors in birth or enrolment calendar years. |
| **DQA-009** | Malformed CCC / NUPI | Minor | CCC number has fewer or more than 10 digits, or includes `.0` decimal formatting. | Correct format to standard 10-digit Master Facility List + serial code (e.g., `1234500001`). |
| **DQA-010** | Unparseable Viral Load | Minor | Viral load text contains ambiguous strings other than `LDL`, `<LDL`, or numeric values. | Contact laboratory for official copy of viral load result form and update register with numeric or LDL value. |
| **DQA-011** | Register CCC Missing in KPLHIV | Major | Client has CCC number in Register sheet but does not appear in KPLHIV cohort tracking sheet. | Enroll client into the KPLHIV tracking workbook for ART appointment and viral load follow-up. |
| **DQA-012** | KPLHIV CCC Missing in Register | Major | Client appears in KPLHIV tracking sheet but has no matching encounter record in Register. | Reconcile program UIC with intake register; verify whether client is an external transfer-in. |

---

## 4. Supervisory Override Procedures

The Supervisory Override mechanism exists to resolve unavoidable data entry timing lags while preserving strict M&E audit compliance.

### When to Use an Override
- A client was tested positive in the last week of the reporting period and has an appointment for ART initiation scheduled for the following week (`DQA-003`).
- A client transferred in from another facility with physical ART documentation pending formal registry transcription (`DQA-002`).
- An external partner referral resulted in confirmed STI treatment before routine community peer screening (`DQA-006`).

### Step-by-Step Override Authorization
1. On the **Data Quality** page, scroll to the **Supervisor Override Console**.
2. Select the specific DQA Rule you wish to exempt.
3. Enter your assigned **Supervisor Security Token**.
4. Enter a mandatory, descriptive **Reason / Justification** (minimum 10 characters). Generic entries like *"approved"* or *"ok"* are rejected.
5. Click **Authorize Override**.
6. The system immediately unlocks the **Export Reports** page, appends the exemption to `runtime/audit/overrides/override_log.json`, and records the supervisor's identifier in the exported Excel **Run Metadata** tab.

---

## 5. Appendix: Provisional Indicators & Architectural Assumptions (D-049)

In compliance with Owner Decision `D-049` (formalised from Open Question `OQ-40`), the following indicators and calculation methodologies are categorized as **PROVISIONAL**. They reflect pragmatic engineering alignments with the legacy Excel templates, pending definitive national M&E guideline consolidation:

### 1. Defined Package Indicator Pathways (`definedpackage_sem`)
- **Assumption:** DATAFLOW supports two alternative calculation pathways for Defined Package:
  - **Pathway 1 (Standard Prevention):** Client received at least 1 Peer Education encounter + Risk Reduction Counselling (RRC) + Condom distribution within the reporting period.
  - **Pathway 2 (Comprehensive Clinical):** In addition to Pathway 1, client received clinical screening (HTS, PrEP, STI, or TB screening).
- **Default Production Setting:** Pathway 1 is active by default to maintain 100% equivalence with historical Sub-Recipient reporting sheets. M&E leads may enable Pathway 2 via population configuration (`config/populations/*.yaml`).

### 2. PrEP Continuation vs. Refill Counting (`prep_refill_sem`)
- **Assumption:** Any encounter during the reporting period where PrEP status is recorded as `'Refill'` or `'Continued'` increments the continuation indicator by client unique ID (`nunique`), regardless of elapsed days between clinic visits.
- **Guideline Ambiguity:** National guidelines recommend a 30-day window for monthly regimens and 90-day window for quarterly regimens. In the absence of longitudinal day-level prescription logs, DATAFLOW evaluates encounter-period presence.

### 3. STI Syndromic Disaggregation vs. Single Case Reporting (`diagnosed_with_sti`)
- **Assumption:** If a client presents with multiple STI syndromes during the same semester (e.g., Urethral Discharge and Genital Ulcer Disease across separate visits), the summary table aggregates unique clients treated rather than total syndrome episodes.
- **Equivalence Note:** Matches notebook Cell 77 cell-by-cell logic.

### 4. Viral Load Suppression Cut-Off (`vl_suppressed`)
- **Assumption:** Viral load results are classified as suppressed if:
  - Text is explicitly `'LDL'`, `'<LDL'`, `'<40'`, `'<50'`, `'<200'`, or `'<400'`.
  - Numeric value is strictly `< 1,000` copies/mL.
- **Guideline Note:** Aligned with Kenya National Guidelines for HIV Treatment (2022). Results between 200 and 999 copies/mL are suppressed per national standard, though flagged for enhanced adherence counselling.

### 5. Age Group Binning & Missing Age Handling (`age_group`)
- **Assumption:** Clients are binned into standard national PEPFAR/NASCOP categories:
  - `Below 15`: Age < 15 years
  - `15-19`: Age 15 to 19 years
  - `20-24`: Age 20 to 24 years
  - `25+`: Age $\ge$ 25 years
  - `(MISSING)`: Age is blank or invalid
- **Exclusion Safeguard:** Records with unrecorded age or unrecorded sex are preserved in total cohort counts and summary tables under `(MISSING)`, but excluded from sex-disaggregated pivot tables with an explanatory footnote per Decision `D-022`.
