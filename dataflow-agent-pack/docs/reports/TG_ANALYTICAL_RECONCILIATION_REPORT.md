# TG ANALYTICAL RECONCILIATION REPORT — DATAFLOW

**Date:** 2026-11-12  
**Dataset:** Real-World Transgender (`reference/Consolidated TG.xlsb`)  
**Reference Benchmark:** `reference/Summary TG.xlsx` (`TG` and `KPI` sheets)  
**Status:** Comprehensive Cell-by-Cell Reconciliation (Phase D & E)  

---

## 1. Executive Summary

This report establishes the cell-by-cell numerical reconciliation between DATAFLOW's independently calculated analytical summaries and the benchmark legacy summaries in `reference/Summary TG.xlsx`.

Reconciliation was conducted across two discrete analytical worksheets:
1. **Sheet 1: `TG` (Service Summary):** 16 County/SR rows × 25 reporting columns = 400 total cells, plus the formula-driven `TOTAL` row.
2. **Sheet 2: `KPI` (KPI Indicators by Age and Sex):** 16 SR/County rows × 24 reporting columns = 384 total cells, plus the aggregated `TOTAL` row.

### Reconciliation Scorecard:
| Analytical Worksheet | Total Cells Evaluated | Baseline Concordance | Post-Correction Concordance | Variance Post-Correction | Status |
|---|---:|---:|---:|---:|:---:|
| **Sheet 1: Service Summary (`TG`)** | 400 data cells + 22 totals | 96.25% (385/400) | **100.00% (400/400)** | **0.00** | **PERFECT PASS** |
| **Sheet 2: KPI Demographic (`KPI`)** | 336 metric cells + 48 dimensions/totals | 0.00% (Stub) | **100.00% (384/384)** | **0.00** | **PERFECT PASS** |
| **Overall Analytical Accuracy** | **784 cells + Totals** | — | **100.00%** | **0.00** | **PERFECT PASS** |

---

## 2. Sheet 1: Service Summary Reconciliation Details

### 2.1 Indicators Evaluated
Every applicable indicator, sub-indicator, and demographic group was independently verified across all 16 reporting rows:
- **Demographics:** `COUNTY`, `SR NAME`, `REGION`, `15-19`, `20-24`, `25+`, `Below 15`.
- **Cohort Totals:** `COHORT` (`TotalCohort`), `PE` (`TotalPE`).
- **HIV Testing & PLHIV:** `Q1` (`HTSQ1`), `NEGQ1` (`HTS_Negative`), `POSQ1` (`HTS_Positive`), `Total_KPLHIV`, `Suppressed`.
- **Defined Package:** `DEFINED PACKAGE` (`DefinedPackage_Q1`).
- **PrEP:** `PREP ` (`PREP_Q1`).
- **ART:** `NEWQ1` (`New_on_ART`), `CURRENTQ1` (`CurrentArt_Q1`).
- **STI:** `STI SCREENING` (`STISCREENEDQ_1`), `STI DIAGNOSIS` (`STIDiagnosid_Q1`), `STI TREATMENT` (`STItreated_Q1`).
- **TB:** `TB SCREENING` (`TB_SCREENED_Q1`).
- **Peer Education:** `PEER EDUCATION` (`PeerEducation_Q1`).
- **Condoms:** `Q1` (`ReceivedCondom_Q1`), `TOTQ1` (`total_condoms_Q1`).

### 2.2 Baseline Discrepancy Log and Root Causes

| Worksheet | Indicator | Dimension / County | Legacy Benchmark | Baseline Value | Variance | Root Cause |
|---|---|---|---:|---:|---:|---|
| Service Summary | DEFINED PACKAGE | Bungoma (MAAYGO) | 517 | 503 | -14 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Kajiado (HOYMAS) | 144 | 143 | -1 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Kajiado (HWWK) | 210 | 202 | -8 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | PREP | Kajiado (HWWK) | 61 | 60 | -1 | Case-sensitivity missed lowercase `'switched'` |
| Service Summary | DEFINED PACKAGE | Kakamega (MAAYGO) | 215 | 207 | -8 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Kilifi (AMKENI-MALINDI) | 384 | 375 | -9 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Kisii (IRDO) | 153 | 146 | -7 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Kwale (PUP-AMKENI) | 100 | 88 | -12 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Laikipia (BHESP) | 185 | 183 | -2 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Migori (IRDO) | 290 | 283 | -7 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Nairobi (ISHTAR) | 129 | 124 | -5 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Nakuru (HWWK) | 110 | 107 | -3 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Siaya (MAAYGO) | 106 | 102 | -4 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Uasin Gishu (NIAK) | 46 | 45 | -1 | Case-sensitivity missed `"Known Positive"` |
| Service Summary | DEFINED PACKAGE | Vihiga (MAAYGO) | 132 | 127 | -5 | Case-sensitivity missed `"Known Positive"` |

### 2.3 Post-Correction Service Summary Full Reconciliation

Following case-normalization across clinical status variables (`Known Positive` and `switched`), every county reconciles with zero variance:

| County | Sub-Recipient | Region | Cohort | PE | HTS Q1 | HTS Neg | HTS Pos | KPLHIV | Suppressed | Defined Package | PrEP | Current ART | STI Screen | TB Screen | PE Q1 | Condom Q1 | Total Condoms | Status |
|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| BUNGOMA | MAAYGO | NRR | 522 | 15 | 503 | 503 | 0 | 14 | 14 | **517** | **375** | 14 | 517 | 517 | 522 | 522 | 13,998 | **PASS** |
| KAJIADO | HOYMAS | LER | 144 | 3 | 143 | 143 | 0 | 1 | 1 | **144** | **54** | 1 | 144 | 144 | 144 | 144 | 5,553 | **PASS** |
| KAJIADO | HWWK | LER | 211 | 7 | 202 | 202 | 0 | 8 | 6 | **210** | **61** | 8 | 210 | 210 | 211 | 211 | 5,429 | **PASS** |
| KAKAMEGA | MAAYGO | NRR | 221 | 6 | 207 | 207 | 0 | 8 | 7 | **215** | **167** | 8 | 215 | 215 | 221 | 221 | 5,846 | **PASS** |
| KILIFI | AMKENI-MALINDI | COR | 416 | 10 | 375 | 375 | 0 | 17 | 7 | **384** | **77** | 17 | 384 | 384 | 416 | 416 | 13,197 | **PASS** |
| KISII | IRDO | WKR | 158 | 5 | 146 | 146 | 0 | 10 | 10 | **153** | **73** | 20 | 153 | 153 | 158 | 158 | 3,561 | **PASS** |
| KWALE | PUP-AMKENI | COR | 100 | 3 | 88 | 88 | 0 | 12 | 3 | **100** | **72** | 12 | 100 | 100 | 100 | 100 | 725 | **PASS** |
| LAIKIPIA | BHESP | LER | 185 | 6 | 183 | 183 | 0 | 2 | 2 | **185** | **183** | 2 | 185 | 185 | 185 | 185 | 1,665 | **PASS** |
| MIGORI | IRDO | WKR | 296 | 11 | 283 | 283 | 0 | 7 | 7 | **290** | **102** | 7 | 290 | 290 | 296 | 296 | 7,880 | **PASS** |
| MOMBASA | PUP-AMKENI | COR | 280 | 7 | 279 | 279 | 0 | 1 | 0 | **279** | **138** | 1 | 279 | 279 | 280 | 280 | 1,472 | **PASS** |
| NAIROBI | ISHTAR | LER | 130 | 3 | 124 | 124 | 0 | 5 | 0 | **129** | **30** | 5 | 130 | 130 | 130 | 130 | 1,191 | **PASS** |
| NAKURU | HWWK | NRR | 114 | 3 | 107 | 107 | 0 | 3 | 3 | **110** | **38** | 3 | 114 | 114 | 114 | 114 | 1,296 | **PASS** |
| SIAYA | MAAYGO | WKR | 109 | 5 | 102 | 102 | 0 | 5 | 5 | **106** | **100** | 5 | 106 | 106 | 109 | 109 | 3,538 | **PASS** |
| TAITA TAVETA | PUP-AMKENI | COR | 52 | 1 | 51 | 51 | 0 | 1 | 0 | **51** | **35** | 1 | 51 | 51 | 52 | 52 | 599 | **PASS** |
| UASIN GISHU | NIAK | NRR | 53 | 2 | 47 | 47 | 0 | 1 | 1 | **46** | **2** | 1 | 48 | 48 | 53 | 51 | 879 | **PASS** |
| VIHIGA | MAAYGO | WKR | 133 | 5 | 127 | 127 | 0 | 5 | 5 | **132** | **109** | 5 | 132 | 132 | 133 | 133 | 5,643 | **PASS** |
| **TOTAL** | **16 Units** | — | **3,124** | **92** | **2,967** | **2,967** | **0** | **100** | **71** | **3,051** | **1,616** | **110** | **3,058** | **3,058** | **3,124** | **3,122** | **72,472** | **100% PASS** |

---

## 3. Sheet 2: KPI Demographic Summary Reconciliation Details

### 3.1 Demographic Disaggregation Structure
Each indicator is disaggregated into 6 gender-age combinations and a total column:
- `15-19_M`, `15-19_F`
- `20-24_M`, `20-24_F`
- `25+_M`, `25+_F`
- `Total`

### 3.2 Cell-by-Cell Reconciliation Table (Indicators: DEFINED PACKAGE, HTS, PREP)

All 16 rows and 21 metric columns match the benchmark with **zero cell differences**:

| Sub-Recipient | Region | County | Defined Package Total | HTS Total | PrEP Total | Discrepancies Detected | Status |
|---|:---:|---|---:|---:|---:|:---:|:---:|
| AMKENI-MALINDI | COR | KILIFI | 384 | 375 | 77 | 0 | **PASS** |
| BHESP | LER | LAIKIPIA | 185 | 183 | 183 | 0 | **PASS** |
| HOYMAS | LER | KAJIADO | 144 | 143 | 54 | 0 | **PASS** |
| HWWK | LER | KAJIADO | 210 | 202 | 61 | 0 | **PASS** |
| HWWK | NRR | NAKURU | 110 | 107 | 38 | 0 | **PASS** |
| IRDO | WKR | KISII | 153 | 146 | 73 | 0 | **PASS** |
| IRDO | WKR | MIGORI | 290 | 283 | 102 | 0 | **PASS** |
| ISHTAR | LER | NAIROBI | 129 | 124 | 30 | 0 | **PASS** |
| MAAYGO | NRR | BUNGOMA | 517 | 503 | 375 | 0 | **PASS** |
| MAAYGO | NRR | KAKAMEGA | 215 | 207 | 167 | 0 | **PASS** |
| MAAYGO | WKR | SIAYA | 106 | 102 | 100 | 0 | **PASS** |
| MAAYGO | WKR | VIHIGA | 132 | 127 | 109 | 0 | **PASS** |
| NIAK | NRR | UASIN GISHU | 46 | 47 | 2 | 0 | **PASS** |
| PUP-AMKENI | COR | KWALE | 100 | 88 | 72 | 0 | **PASS** |
| PUP-AMKENI | COR | MOMBASA | 279 | 279 | 138 | 0 | **PASS** |
| PUP-AMKENI | COR | TAITA TAVETA | 51 | 51 | 35 | 0 | **PASS** |
| **TOTAL** | — | — | **3,051** | **2,967** | **1,616** | **0** | **100% PASS** |

### 3.3 Demographic Disaggregation Totals Reconciliation
| Indicator | 15–19_M | 15–19_F | 20–24_M | 20–24_F | 25+_M | 25+_F | Total | Status |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| **DEFINED PACKAGE** | 7 | 25 | 504 | 466 | 1,184 | 865 | **3,051** | **100% PASS** |
| **HTS** | 7 | 25 | 494 | 460 | 1,132 | 849 | **2,967** | **100% PASS** |
| **PREP** | 2 | 18 | 296 | 290 | 582 | 428 | **1,616** | **100% PASS** |

---

## 4. Population-Specific Defined Package Verification

The audit explicitly verified that:
1. **NSP Requirement:** In accordance with BR-001 and `POPULATION_RULES.md`, TG does NOT require NSP in its Defined Package pathways. (NSP is exclusively mandated for PWID).
2. **Dual Clinical Pathways:**
   - **General Pathway:** $\text{HTS} \land \text{STI\_Screening} \land \text{TB\_Screening} \land \text{Condoms} \land \text{HE\_RRC} \rightarrow 2,965 \text{ clients}$.
   - **PLHIV Pathway:** $\text{Known\_Positive} \land \text{STI\_Screening} \land \text{TB\_Screening} \land \text{Condoms} \land \text{HE\_RRC} \rightarrow 86 \text{ clients}$.
   - **Composite Total:** $2,965 + 86 = 3,051 \text{ clients}$.
3. **Unique-Client Counting:** Calculations operate on unique client identifiers (`kp_vp_unique_identifier_code`), preventing duplicate visit inflation.

---

## 5. Conclusion
DATAFLOW reproduces both legacy TG analytical summary sheets with **100.00% precision**:
- Zero numerical discrepancies across all 784 data cells.
- Zero column alignment errors.
- 100% agreement on all row, column, and grand totals.
