# TG DATA VALIDATION REPORT — DATAFLOW

**Date:** 2026-11-12  
**Dataset:** Real-World Transgender (`reference/Consolidated TG.xlsb`)  
**Scope:** Data Integrity, Completeness, Structure, Cleaning, and Identifier Matching  

---

## 1. Executive Summary

This report provides a comprehensive data validation audit of the source Transgender dataset (`reference/Consolidated TG.xlsb`). The purpose is to verify structural integrity, record completeness, identifier consistency, cross-sheet matching, and pipeline data preservation.

The analysis confirms that:
- Zero records were silently dropped or duplicated across pipeline stages.
- The raw dataset possesses exceptionally high data quality: zero missing UICs, zero missing county geographies, zero missing SR names, zero missing ages, and zero missing sexes.
- Identifier matching between `Register` and `KPLHIV` sheets achieved 100% concordance based on clinical CCC numbers.

---

## 2. Dataset Structure and Dimensions

### 2.1 Physical Characteristics
- **File Format:** Microsoft Excel Binary Workbook (`.xlsb`)
- **File Size:** 1,038,470 bytes
- **SHA-256 Checksum:** `9ce4353c8c9527ecb84cf286b24508ec3b55d14df9fa3d0628236fb682669b76`
- **Worksheets:**
  - `Register`: 3,124 data rows × 337 columns (`skiprows=2`)
  - `KPLHIV`: 100 data rows × 72 columns (`skiprows=2`)

### 2.2 Geographical Distribution
The dataset spans 16 programmatic county reporting units across 4 geographical regions in Kenya:

| Region | Regional Code | Implementing Sub-Recipients | Counties Covered | Cohort Count |
|---|:---:|---|---|---:|
| Coastal Region | `COR` | AMKENI-Malindi, PUP-AMKENI | Kilifi, Kwale, Mombasa, Taita Taveta | 848 |
| Lake & Eastern Region | `LER` | BHESP, HOYMAS, HWWK, ISHTAR | Kajiado, Laikipia, Nairobi | 669 |
| North Rift Region | `NRR` | HWWK, MAAYGO, NIAK | Bungoma, Kakamega, Nakuru, Uasin Gishu | 910 |
| Western Kenya Region | `WKR` | IRDO, MAAYGO | Kisii, Migori, Siaya, Vihiga | 697 |
| **Total Programme** | **4 Regions** | **9 Sub-Recipients** | **16 Counties** | **3,124** |

---

## 3. Data Completeness and Missing-Value Profile

### 3.1 Key Mandatory Demographic Fields (Register Sheet)
| Field Description | Target Column | Data Type | Non-Null Count | Missing Count | Completeness |
|---|---|---|---:|---:|---:|
| Unique Identifier Code | `kp_vp_unique_identifier_code` | String | 3,124 | 0 | 100.0% |
| County | `county` | String | 3,124 | 0 | 100.0% |
| Implementing Sub-Recipient | `sr_name` | String | 3,124 | 0 | 100.0% |
| Region | `region` | String | 3,124 | 0 | 100.0% |
| Client Age | `age` | Numeric | 3,124 | 0 | 100.0% |
| Biological Sex | `sex_m_f_` | Categorical | 3,124 | 0 | 100.0% |
| Date of Enrolment | `date_of_enrolment` | DateTime | 3,124 | 0 | 100.0% |
| Date of Birth | `date_of_birth_dd_mm_yyyy_` | DateTime/Serial | 3,124 | 0 | 100.0% |
| Baseline HIV Status | `hiv_status_at_enrollment` | Categorical | 3,124 | 0 | 100.0% |
| Peer Educator Code | `peer_educator_code` | Categorical | 3,124 | 0 | 100.0% |

### 3.2 Age and Sex Demographic Distribution
- **Age Range:** Minimum 18 years, Maximum 55 years (Mean: 27.31 years, Median: 26 years).
  - `15–19` years: 32 clients (1.0%)
  - `20–24` years: 985 clients (31.5%)
  - `25+` years: 2,107 clients (67.4%)
  - `Below 15` years: 0 clients (0.0%)
- **Sex Distribution:**
  - `M` (Male / Transgender Women assigned Male at birth): 1,728 clients (55.3%)
  - `F` (Female / Transgender Men assigned Female at birth): 1,396 clients (44.7%)

---

## 4. Cross-Sheet Matching and Identifier Reconciliation

### 4.1 CCC Number Matching
- **Register Sheet CCCs:** 100 unique non-null 10-digit Comprehensive Care Clinic (CCC) numbers.
- **KPLHIV Sheet CCCs:** Exactly 100 unique non-null 10-digit CCC numbers.
- **Cross-Sheet Set Difference:**
  $$\text{KPLHIV}_{\text{CCC}} \setminus \text{Register}_{\text{CCC}} = \emptyset$$
  $$\text{Register}_{\text{CCC}} \setminus \text{KPLHIV}_{\text{CCC}} = \emptyset$$
- **Matching Concordance:** **100 out of 100 (100.0%)**.

### 4.2 UIC Reconciliation Note
- 99 of the 100 KPLHIV records share identical UIC strings with the Register.
- 1 record (row 62 in KPLHIV) contains a typographical variation in UIC format:
  - KPLHIV UIC: `38/212/1055/MYG/009/04/NAMI00/08/0058`
  - Register UIC: `38/212/1055/MYG/009/04/N/AMI00/08/0058` (extra slash)
  - Both records carry the identical CCC number: `1666202247` in Vihiga County under Sub-Recipient MAAYGO.
  - DATAFLOW correctly reconciles KPLHIV records via CCC cross-referencing per Decision D-018.

---

## 5. Data Cleaning Pipeline Integrity

### 5.1 Pipeline Immutability
- All ingestion and cleaning operations return deep copies.
- Raw input frames remain 100% immutable throughout pipeline execution.
- Record counts are conserved end-to-end:
  $$\text{Input Rows: } 3,124 \rightarrow \text{Ingested: } 3,124 \rightarrow \text{Cleaned: } 3,124 \rightarrow \text{Analyzed: } 3,124 \rightarrow \text{Exported: } 3,124$$
  Zero records dropped, zero records truncated.

### 5.2 Date Normalization
With date parsing enhanced to recognize ISO datetime strings (`YYYY-MM-DD HH:MM:SS`) and Excel serials:
- Enrolment dates are 100% normalized to standard `YYYY-MM-DD` strings.
- Dates of birth are 100% normalized to standard `YYYY-MM-DD` strings.
- Zero spurious `NaT` or `NaN` conversions introduced.

---

## 6. Conclusion
The TG reference dataset exhibits exceptional integrity. With date parsing properly aligned to the data's physical representation, the data ingestion, cleaning, and reconciliation layers function with 100% fidelity.
