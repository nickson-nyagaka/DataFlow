# TG REFERENCE INVENTORY — DATAFLOW

**Date:** 2026-11-12  
**Dataset:** Transgender (TG) Key Population  
**Status:** Complete Reference Inspection (Phase A)  

---

## 1. Executive Summary

This inventory documents all reference files, worksheets, dimensions, column structures, header layouts, and indicator definitions for the Transgender (TG) dataset in DATAFLOW. The source dataset reflects real-world clinical and outreach services provided to transgender key population clients across 16 counties and implementing Sub-Recipients in Kenya.

All inspections were performed without modifying original reference workbooks.

---

## 2. Reference Files Inventory

| File Name | Location | Format | File Size | Description |
|---|---|---|---:|---|
| `Consolidated TG.xlsb` | `reference/Consolidated TG.xlsb` | Excel Binary Workbook (`.xlsb`) | 1,038,470 bytes | Raw client-level service records and KPLHIV tracking sheet. |
| `Summary TG.xlsx` | `reference/Summary TG.xlsx` | OpenXML Workbook (`.xlsx`) | 14,078 bytes | Legacy reference summary workbook containing 2 analytical sheets. |
| `OPTIMIZED_DATA_MGT.sanitized.ipynb` | `reference/OPTIMIZED_DATA_MGT.sanitized.ipynb` | Jupyter Notebook (`.ipynb`) | 148,537 bytes | Legacy data management pipeline notebook (87 cells). |
| `KP_TEMPLATE.xlsx` | `reference/KP_TEMPLATE.xlsx` | OpenXML Workbook (`.xlsx`) | 30,562 bytes | Standard reporting workbook template and layout definitions. |

---

## 3. Raw Dataset Structure (`Consolidated TG.xlsb`)

### 3.1 Worksheets Overview

| Sheet Name | Data Purpose | Header Row Index | Data Rows | Total Columns | Unique UICs | Missing UICs | Duplicate UICs |
|---|---|:---:|---:|---:|---:|---:|---:|
| `Register` | Longitudinal client service records | Row 3 (`skiprows=2`) | 3,124 | 337 | 3,124 | 0 | 0 |
| `KPLHIV` | KP Living with HIV clinical tracking | Row 3 (`skiprows=2`) | 100 | 72 | 100 | 0 | 0 |

### 3.2 Header Layout (`Register` Sheet)
- **Row 1 (Metadata Banner):** `KVP COHORT REGISTER` followed by numeric timestamps.
- **Row 2 (Thematic Blocks):** Group headers:
  - Columns 1–8: `ADDRESS`
  - Columns 9–13: `TYPOLOGY & DEMOGRAPHY`
  - Columns 14–19: `CONTACT, ENROLLMENT & PE`
  - Columns 20–25: `JULY 2026 - (1). PE, HIV services, HTS & ART`
  - Columns 26–34: `JULY 2026 (2). TB & PEP`
  - Columns 35–38: `JULY 2026 (3). Condom & Lubricant`
  - Columns 39–40: `JULY 2026 (4). NSP`
  - Columns 41–48: `JULY 2026 (5). Hep B & Hep C`
  - Columns 49–75: `JULY 2026 (6). STI Screening, PrEP & Mental Health`
  - Repeats across subsequent monthly cohorts (August 2026 through December 2026, totaling 6 months).
- **Row 3 (Column Header Names):** 337 distinct column names.

### 3.3 Key Identification & Demographic Columns

| Physical Column Name | Normalized Field | Data Type | Missing Count | Valid Values / Distribution |
|---|---|---|---:|---|
| `Region` | `region` | String | 0 | NRR, LER, COR, WKR |
| `SR Name` | `sr_name` | String | 0 | MAAYGO, HOYMAS, HWWK, AMKENI-Malindi, IRDO, PUP-AMKENI, BHESP, ISHTAR, NIAK |
| `County` | `county` | String | 0 | 16 counties (Bungoma, Kajiado, Kilifi, Kisii, Kwale, Kakamega, Laikipia, Migori, Mombasa, Nairobi, Nakuru, Siaya, Taita Taveta, Uasin Gishu, Vihiga) |
| `Sub-County` | `sub_county` | String | 0 | Programmatic sub-counties |
| `KP/VP unique identifier code ` | `kp_vp_unique_identifier_code` | String | 0 | 3,124 distinct valid alphanumeric UIC strings |
| `Key/Vulnerable population Type ` | `key_vulnerable_population_type` | String | 0 | TG |
| `Date of Birth (DD/MM/YYYY)` | `date_of_birth_dd_mm_yyyy_` | Date/String | 0 | Serial numbers, ISO strings, DD/MM/YYYY |
| `Age ` | `age` | Float/Int | 0 | Min: 18, Max: 55, Mean: 27.31 |
| `Sex (M/F) ` | `sex_m_f_` | String | 0 | M: 1,728 (55.3%), F: 1,396 (44.7%) |
| `Date of enrolment ` | `date_of_enrolment` | Date/String | 0 | ISO strings (`YYYY-MM-DD HH:MM:SS`) |
| `HIV status at enrollment` | `hiv_status_at_enrollment` | String | 0 | Negative (3,024), Known Positive (100) |
| `CCC Number/NUPI/N/A (10 digit number)` | `ccc_number_nupi_n_a_10_digit_number_` | String/Float | 3,024 | 100 valid 10-digit CCC numbers |
| `Peer Educator Code` | `peer_educator_code` | String | 0 | 92 distinct PE codes |

---

## 4. Legacy Summary Workbook Structure (`Summary TG.xlsx`)

The workbook contains exactly TWO analytical summary sheets:

### 4.1 Sheet 1: `TG` (Service Summary)
- **Dimensions:** 19 rows × 25 columns.
- **Rows 1–2:** Multi-level merged group headers and subheaders.
- **Rows 3–18:** 16 County × SR × Region data breakdown rows.
- **Row 19:** `TOTAL` row containing dynamic `=SUM()` formulas across columns 4 to 25.

#### Column Mapping and Header Hierarchy:
| Col Index | Excel Col | Group Header (Row 1) | Subheader (Row 2) | Target Field / Indicator | Formula (Row 19) |
|:---:|:---:|---|---|---|:---:|
| 1 | A | COUNTY | *(blank)* | `county` | *(merged A19:C19)* |
| 2 | B | SR NAME | *(blank)* | `sr_name` | *(merged)* |
| 3 | C | REGION | *(blank)* | `region` | *(merged)* |
| 4 | D | AGE GROUP | 15-19 | `15-19` | `=SUM(D3:D18)` |
| 5 | E | AGE GROUP | 20-24 | `20-24` | `=SUM(E3:E18)` |
| 6 | F | AGE GROUP | 25+ | `25+` | `=SUM(F3:F18)` |
| 7 | G | AGE GROUP | Below 15 | `Below 15` | `=SUM(G3:G18)` |
| 8 | H | TOTAL | COHORT | `TotalCohort` | `=SUM(H3:H18)` |
| 9 | I | TOTAL | PE | `TotalPE` | `=SUM(I3:I18)` |
| 10 | J | HIV TESTING & PLHIV | Q1 | `HTSQ1` | `=SUM(J3:J18)` |
| 11 | K | HIV TESTING & PLHIV | NEGQ1 | `HTS_Negative` | `=SUM(K3:K18)` |
| 12 | L | HIV TESTING & PLHIV | POSQ1 | `HTS_Positive` | `=SUM(L3:L18)` |
| 13 | M | HIV TESTING & PLHIV | Total_KPLHIV | `Total_KPLHIV` | `=SUM(M3:M18)` |
| 14 | N | HIV TESTING & PLHIV | Suppressed | `Suppressed` | `=SUM(N3:N18)` |
| 15 | O | DEFINED PACKAGE | *(blank)* | `DefinedPackage_Q1` | `=SUM(O3:O18)` |
| 16 | P | PREP | *(blank)* | `PREP_Q1` | `=SUM(P3:P18)` |
| 17 | Q | ART | NEWQ1 | `New_on_ART` | `=SUM(Q3:Q18)` |
| 18 | R | ART | CURRENTQ1 | `CurrentArt_Q1` | `=SUM(R3:R18)` |
| 19 | S | STI SCREENING | *(blank)* | `STISCREENEDQ_1` | `=SUM(S3:S18)` |
| 20 | T | STI DIAGNOSIS | *(blank)* | `STIDiagnosid_Q1` | `=SUM(T3:T18)` |
| 21 | U | STI TREATMENT | *(blank)* | `STItreated_Q1` | `=SUM(U3:U18)` |
| 22 | V | TB SCREENING | *(blank)* | `TB_SCREENED_Q1` | `=SUM(V3:V18)` |
| 23 | W | PEER EDUCATION | *(blank)* | `PeerEducation_Q1` | `=SUM(W3:W18)` |
| 24 | X | CONDOMS | Q1 | `ReceivedCondom_Q1` | `=SUM(X3:X18)` |
| 25 | Y | CONDOMS | TOTQ1 | `total_condoms_Q1` | `=SUM(Y3:Y18)` |

---

### 4.2 Sheet 2: `KPI` (KPI Indicators by Age and Sex)
- **Dimensions:** 19 rows × 24 columns.
- **Rows 1–2:** Group headers (`DEMOGRAPHICS`, `DEFINED PACKAGE`, `HTS`, `PREP`) and subheaders (`SR  NAME`, `REGION`, `COUNTY`, and the 7 age-sex columns per indicator).
- **Rows 3–18:** 16 SR × Region × County data breakdown rows.
- **Row 19:** `TOTAL` row containing aggregated integer totals.

#### Column Mapping and Demographic Subcategories:
| Col Range | Excel Cols | Indicator Block (Row 1) | Subheaders (Row 2) |
|---|---|---|---|
| Cols 1–3 | A–C | `DEMOGRAPHICS` | `SR  NAME`, `REGION`, `COUNTY` |
| Cols 4–10 | D–J | `DEFINED PACKAGE` | `15-19_M`, `15-19_F`, `20-24_M`, `20-24_F`, `25+_M`, `25+_F`, `Total` |
| Cols 11–17 | K–Q | `HTS` | `15-19_M`, `15-19_F`, `20-24_M`, `20-24_F`, `25+_M`, `25+_F`, `Total` |
| Cols 18–24 | R–X | `PREP` | `15-19_M`, `15-19_F`, `20-24_M`, `20-24_F`, `25+_M`, `25+_F`, `Total` |

---

## 5. Geographical Breakdown Inventory

The 16 reporting rows common to both summary sheets represent the complete reporting matrix:

| Row | County | Sub-Recipient (SR) | Region | Cohort Size (Register) | KPLHIV Size |
|:---:|---|---|:---:|---:|---:|
| 1 | Bungoma | MAAYGO | NRR | 522 | 14 |
| 2 | Kajiado | HOYMAS | LER | 144 | 1 |
| 3 | Kajiado | HWWK | LER | 211 | 8 |
| 4 | Kakamega | MAAYGO | NRR | 221 | 8 |
| 5 | Kilifi | AMKENI-MALINDI | COR | 416 | 17 |
| 6 | Kisii | IRDO | WKR | 158 | 10 |
| 7 | Kwale | PUP-AMKENI | COR | 100 | 12 |
| 8 | Laikipia | BHESP | LER | 185 | 2 |
| 9 | Migori | IRDO | WKR | 296 | 7 |
| 10 | Mombasa | PUP-AMKENI | COR | 280 | 1 |
| 11 | Nairobi | ISHTAR | LER | 130 | 5 |
| 12 | Nakuru | HWWK | NRR | 114 | 3 |
| 13 | Siaya | MAAYGO | WKR | 109 | 5 |
| 14 | Taita Taveta | PUP-AMKENI | COR | 52 | 1 |
| 15 | Uasin Gishu | NIAK | NRR | 53 | 1 |
| 16 | Vihiga | MAAYGO | WKR | 133 | 5 |
| **TOTAL** | **16 Units** | **9 SRs** | **4 Regions** | **3,124** | **100** |
