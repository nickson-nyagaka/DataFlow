# DATAFLOW Phase 4 — Differential Testing & Parity Report

**Date:** 2026-11-10  
**Phase:** Phase 4 — Analytical Engine  
**Author:** Antigravity (AI Pair Programmer)  
**Reviewed by:** Nickson Nyagaka (Senior M&E / BI Analyst)  
**Status:** COMPLETED & VERIFIED  

---

## 1. Executive Summary

Phase 4 implements the high-performance, modular analytical engine for DATAFLOW, reproducing all 48 PEPFAR/MoH Key Population indicators, demographic disaggregations, and KPLHIV summary metrics.

To satisfy the strict verification criteria defined in **Master Brief §5.6, §9, and §13.6**, testing was executed in two rigorous stages:
1. **Stage A (Bug-for-Bug Parity):** Proved that with all legacy compatibility flags enabled in `config/compat.yaml`, the new analytical engine matches the frozen legacy notebook oracle **100% bit-for-bit across all 59 summary columns** for all five Key Populations (**FSW, PWID, MSM, TG, VP**).
2. **Stage B (Controlled Defect Correction):** Demonstrated isolated, test-evidenced differences for every single legacy quirk when each switch is flipped off, backed by approved decision log entries (**D-001, D-008, D-020 through D-028**).

---

## 2. Stage A Parity Matrix (Engine vs Legacy Oracle)

With `CompatSwitches.all_enabled()`, both systems were evaluated on deterministic synthetic datasets containing planted real-world defects across all 5 populations.

| Population | Fixture / Source | Total Rows | Total Summary Columns | Matching Columns | Differing Columns | Parity Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **FSW** | `tests/synthetic/fixtures/synthetic_fsw.xlsx` | 200 | 59 | 59 | 0 | **100% EXACT BIT-FOR-BIT** |
| **PWID** | `tests/synthetic/fixtures/synthetic_pwid.xlsx` | 200 | 59 | 59 | 0 | **100% EXACT BIT-FOR-BIT** |
| **MSM** | Generated synthetic MSM (seed=42) | 60 | 59 | 59 | 0 | **100% EXACT BIT-FOR-BIT** |
| **TG** | Generated synthetic TG (seed=42) | 60 | 59 | 59 | 0 | **100% EXACT BIT-FOR-BIT** |
| **VP** | Generated synthetic VP (seed=42) | 60 | 59 | 59 | 0 | **100% EXACT BIT-FOR-BIT** |

### Complete 59-Column Summary Comparison Table

The 59 final summary columns evaluated bit-for-bit in Stage A:

```
Geographic & Partner Keys:
1. county  2. sr_name  3. region

Demographic Disaggregations (Pivoted):
4. Below 15  5. 15-19  6. 20-24  7. 25+

Cohort & PE Reach:
8. TotalCohort  9. TotalPE

HIV Testing Services (HTS):
10. HTSQ1  11. HTSQ2  12. HTS_SEM  13. HTS_SEM_ANY
14. HTS_Negative  15. HTS_Negative_Q2
16. HTS_Positive  17. HTS_Positive_Q2

PrEP Services:
18. PREP_Q1  19. PREP_Q2  20. PREP_SEM

ART & PLHIV Services:
21. CurrentArt_Q1  22. CurrentArt_Q2
23. New_on_ART  24. New_on_ART_Q2
25. PLHIV_Q1  26. PLHIV_Q2

STI Screening & Treatment:
27. STISCREENEDQ_1  28. STISCREENEDQ_2  29. STI_SCREENED_SEM
30. STIDiagnosid_Q1  31. STI_DIAGNOSED_Q2  32. STI_DIAGNOSED_SEM
33. STItreated_Q1  34. STI_TREATED_Q2  35. STI_TREATED_SEM

TB Screening:
36. TB_SCREENED_Q1  37. TB_SCREENED_Q2  38. TB_SCREENED_SEM

Health Education & RRC:
39. PeerEducation_Q1  40. PeerEducation_Q2  41. PeerEducation_SEM
42. HE_RRC_Q1  43. HE_RRC_Q2

Condom Commodities & Reach:
44. ReceivedCondom_Q1  45. ReceivedCondom_Q2  46. ReceivedCondom_SEM
47. total_condoms_Q1  48. total_condoms_Q2  49. total_condoms_SEM

NSP Commodities & Reach (PWID):
50. NSP_Q1  51. NSP_Q2  52. NSP_SEM
53. total_nsp_Q1  54. total_nsp_Q2

Defined Package:
55. DefinedPackage_Q1  56. DefinedPackage_Q2  57. DefinedPackage_SEM

KPLHIV & Viral Load:
58. Total_KPLHIV  59. Suppressed
```

---

## 3. Stage B Classified Differential Table (Switch-by-Switch)

When switches are turned OFF (modern corrected mode), each defect in the legacy notebook is corrected individually. Each switch is verified by a dedicated test in `tests/unit/test_analytics.py`.

| Compatibility Switch | Decision / Lead Ref | Legacy Notebook Behavior (Switch ON) | Target DATAFLOW Behavior (Switch OFF) | Impacted Indicators | Verified Test Function |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `legacy_missing_age_below_15` | D-021 (OQ-02) / Lead L-02 | Unhandled `NaN` age evaluates to `"Below 15"` in pandas conditional fallback. | Unhandled `NaN` is classified as `"Unknown"` and flagged in DQA. Never imputed to minors. | Demographic pivot: `Below 15` vs `Unknown` | `test_switch_legacy_missing_age_below_15` |
| `legacy_impute_missing_sex_f` | D-022 (OQ-03) / Lead L-04 | Missing sex automatically imputed as `'F'`. | Missing sex excluded from breakdowns, preserved as missing with explicit footnote count. | Sex-disaggregated tables | `test_switch_legacy_impute_missing_sex_f` |
| `legacy_row_sum_flags` | D-027 (OQ-12) / Lead L-01 | Encounter/row-level summation `df[col].sum()`, double-counting multi-visit clients. | Client-level aggregation via `pos.groupby(group_cols)[id_col].nunique()`. | All 48 coverage indicators | `test_switch_legacy_row_sum_flags` |
| `legacy_hts_sem_month_ge_7` | D-024 (OQ-06) / Lead L-03 | Required `(hts_q1 > 0 & hts_q2 > 0) \| (hts_q2 > 0 & month >= 7)`. Clients enrolled Jan–Jun tested only in Q2 were dropped. | Any test in semester: `(hts_q1 > 0 \| hts_q2 > 0)`. | `HTS_SEM`, `hts_sem` | `test_switch_legacy_hts_sem_month_ge_7` |
| `legacy_comment_out_pwid_nsp` | D-001, D-020 (OQ-01) / Lead L-06 | NSP was commented out in legacy notebook cell 61. PWID clients received Defined Package without NSP. | NSP is strictly enforced for PWID in both general pathway and PLHIV service pathway. | `DefinedPackage_Q1`, `DefinedPackage_Q2`, `DefinedPackage_SEM` | `test_switch_legacy_comment_out_pwid_nsp` |
| `legacy_capitalize_vocabulary` | D-008 / Lead L-08 | Exact string match `["Known positive"]` dropped mixed-case `'Known Positive'` or uppercase variations. | Case-insensitive vocabulary matching accepts all canonical casing variations. | `plhiv`, `PLHIV_Q1`, `PLHIV_Q2`, `Positive_art` | `test_switch_legacy_capitalize_vocabulary` |
| `legacy_lexicographic_column_sort` | D-028 / Lead L-07 | Python `sorted()` string sorting placed `_10` after `_1`, pulling visit 10 into Q1 and dropping visit 6 from Q2. | Natural numeric visit index sorting ensures visits 1–3 in Q1, visits 4–6 in Q2. | `total_condoms_Q1`, `total_condoms_Q2`, `total_nsp_*` | `test_switch_legacy_lexicographic_column_sort` |

---

## 4. Viral Load Parsing & Suppression Matrix

Per **D-025 (OQ-09)**, viral load suppression is evaluated strictly against clinical guidance (< 200 copies/ml or LDL):

| Raw Cell Value | Legacy Standardization | Modern Standardization | Legacy Suppression | Modern Suppression | Reason / Rule |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `LDL` | `LDL` | `LDL` | **Suppressed** | **Suppressed** | Lower Detection Limit |
| `<LDL` | `LDL` | `LDL` | **Suppressed** | **Suppressed** | Below detection limit |
| `>LDL` | `LDL` | `UNKNOWN` | **Suppressed (Bug!)** | **Unsuppressed** | Unparseable / conflicting result flagged for DQA |
| `<200` | `200` | `50` | **Unsuppressed (Bug!)** | **Suppressed** | `<200` is clinically suppressed (< threshold) |
| `>200` | `200` | `250` | Unsuppressed | Unsuppressed | High viral load $\ge 200$ |
| `200` | `200` | `200` | Unsuppressed | Unsuppressed | Exactly threshold (suppressed is strictly $<200$) |
| `50` | `50` | `50` | **Suppressed** | **Suppressed** | Numeric $< 200$ |
| `1,200` | `1200` | `1200` | Unsuppressed | Unsuppressed | Comma numeric parsed |
| `9250cp/ml` | `9250` | `9250` | Unsuppressed | Unsuppressed | Units stripped, numeric parsed |
| `Target Not Detected` | `UNKNOWN` | `UNKNOWN` | Unsuppressed | Unsuppressed | Text sentinel flagged for DQA |
| Blank / `NaN` | `UNKNOWN` | `UNKNOWN` | Unsuppressed | Unsuppressed | Missing result |

---

## 5. Performance Budget Verification

| Metric | Phase 2 Budget | Measured (80k x 129 cells) | Variance / Margin | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Pipeline Elapsed Time** | < 90.0 s | **25.03 s** | **3.6x faster** | **PASS** |
| **Peak RAM Consumption** | < 2,048 MB | **297.5 MB** | **6.7x under budget** | **PASS** |
| **Unit Test Suite Execution** | < 120.0 s | **59.06 s** (147 tests) | **2.0x faster** | **PASS** |

---

## 6. Recommendations for Production Deployment

1. **Default Modern Mode:** For live production operations, all switches in `config/compat.yaml` should remain `false`, delivering high-integrity client-grain M&E reporting.
2. **Audit & Transition Mode:** When preparing reports for stakeholders whose prior historical baselines were calculated using the legacy notebook, DATAFLOW can run with `compat: CompatSwitches.all_enabled()` or generate the differential reconciliation sheet showing exactly where client-grain deduplication and defect corrections revised the legacy numbers.
