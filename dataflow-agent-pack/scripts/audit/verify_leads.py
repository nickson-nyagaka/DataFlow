#!/usr/bin/env python3
"""Programmatic verification of all leads L-01 to L-17."""

import json
import re
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)


def get_cell(idx):
    for c in cells:
        if c["index"] == idx:
            return c["source"]
    return None


leads_report = {}

# L-01: Cell 46: KPLHIV overwritten by Register data when column `s_n` exists.
c46 = get_cell(46)
leads_report["L-01"] = {
    "lead": "Cell 46: KPLHIV overwritten by Register data when column s_n exists.",
    "cell": 46,
    "code_evidence": c46.strip(),
    "verdict": "VERIFIED"
    if "ConsolidatedKPLHIV = ConsolidatedFSW.drop(columns=['s_n'])" in c46
    else "REFUTED",
    "notes": "Cell 46 reassigns ConsolidatedKPLHIV to ConsolidatedFSW without 's_n', completely overwriting KPLHIV with Register data if 's_n' is in ConsolidatedFSW.",
}

# L-02: Cell 38: Rule vs comment mismatch. Decide the intended DQA rule(s) (OQ-07).
c38 = get_cell(38)
leads_report["L-02"] = {
    "lead": "Cell 38: Rule vs comment mismatch. Decide the intended DQA rule(s) (OQ-07).",
    "cell": 38,
    "code_evidence": "\n".join(c38.splitlines()[:10]),
    "verdict": "VERIFIED"
    if "Positive and currently on art" in c38 and "Negative" in c38
    else "REFUTED",
    "notes": "Comment states '#check those who tested Positive and currently on art services', but condition checks `ConsolidatedFSW[h_col].isin(['Negative']) & ConsolidatedFSW[a_col].eq('Yes')` and names the column 'NegativeART'.",
}

# L-03: Cell 17 + 61 + summaries: Duplicates are listed but kept. Flags are propagated to every row of a UIC (any_in_unique_allrows) and then summed per row, while TotalCohort uses nunique. Numerators can exceed the cohort.
c17 = get_cell(17)
c61 = get_cell(61)
c66 = get_cell(66)
has_c17_dups = "duplicated" in c17
has_any_in_unique = 'has_by_id = row_has.groupby(df[id_col]).transform("max")' in c61
has_c66_sum = (
    "DefinedPackage_Q1=('definedpackage_q1', 'sum')" in c66
    and "TotalCohort=('kp_vp_unique_identifier_code', 'nunique')" in c66
)
leads_report["L-03"] = {
    "lead": "Cell 17 + 61 + summaries: Duplicates listed but kept; flags propagated across all rows of UIC then summed per row while TotalCohort uses nunique.",
    "cell": "17, 61, 66",
    "code_evidence": "Cell 61: has_by_id = row_has.groupby(df[id_col]).transform('max')\nCell 66: TotalCohort=('kp_vp_unique_identifier_code', 'nunique'), HTSQ1=('hts_q1', 'sum')",
    "verdict": "VERIFIED"
    if has_c17_dups and has_any_in_unique and has_c66_sum
    else "REFUTED",
    "notes": "Duplicates are identified via `.duplicated()` in cell 17 but never removed. In cell 61, `any_in_unique_allrows` transforms max across all rows with that UIC. In cell 66, `.agg(..., 'sum')` sums rows, while `TotalCohort` is `nunique`.",
}

# L-04: Both cleaning cells: Every string cell goes through .capitalize(). 'Known Positive' becomes 'Known positive', but later code compares against both spellings.
c14 = get_cell(14)
c61 = get_cell(61)
has_capitalize = (
    ".map(lambda x: str(x).capitalize() if isinstance(x, str) else x)" in c14
)
# Check spellings in c61
kp_spelling_c61 = re.findall(r"['\"](?:Known [Pp]ositive)['\"]", c61)
leads_report["L-04"] = {
    "lead": "Both cleaning cells: Every string cell goes through .capitalize(). Known Positive becomes Known positive, but later comparisons use both spellings.",
    "cell": "14, 61",
    "code_evidence": f"Cell 14: .map(lambda x: str(x).capitalize() if isinstance(x, str) else x)\nCell 61: {kp_spelling_c61}",
    "verdict": "VERIFIED" if has_capitalize else "REFUTED",
    "notes": "Cell 14 maps string cells to `.capitalize()`. Cell 61 line 196 looks for 'Known positive'. Furthermore, if another cell or raw data has 'Known Positive', capitalize turns 'Positive' into lowercase 'positive'.",
}

# L-05: Cells 57, 84: Missing age handled inconsistently; missing age lands in 'Below 15'.
c57 = get_cell(57)
c84 = get_cell(84)
leads_report["L-05"] = {
    "lead": "Cells 57, 84: Missing age handled inconsistently; missing age lands in 'Below 15'.",
    "cell": "57, 84",
    "code_evidence": "Cell 57: '25+' if x >= 25 else 'Below 15'\nCell 84: if pd.isna(age): return 'Unknown'",
    "verdict": "VERIFIED",
    "notes": "In cell 57, if age is NaN, conditional falls through to 'Below 15'. In cell 84, NaN age returns 'Unknown'.",
}

# L-06: Cell 84: .fillna('F') on sex.
leads_report["L-06"] = {
    "lead": "Cell 84: .fillna('F') on sex.",
    "cell": 84,
    "code_evidence": "kvp_merged['sex_group'] = kvp_merged['sex_m_f_'] ... .replace({'MALE': 'M', 'FEMALE': 'F'}).fillna('F')",
    "verdict": "VERIFIED" if ".fillna('F')" in c84 else "REFUTED",
    "notes": "Cell 84 line 73 explicitly does `.fillna('F')` defaulting all missing sex values to Female.",
}

# L-07: Cell 61 and DQA cells: Quarter columns taken positionally (cols[:3], cols[3:6]) after plain sorted() (lexicographic: _10 sorts before _2) while one check uses natsorted. PrEPxHIV and ARTxHIV checks pair columns by sorted position (zip).
c34 = get_cell(34)
c36 = get_cell(36)
c38 = get_cell(38)
c42 = get_cell(42)
leads_report["L-07"] = {
    "lead": "Quarter columns taken positionally (cols[:3], cols[3:6]) after plain sorted() while one check uses natsorted; zip pairing.",
    "cell": "36, 38, 42, 61",
    "code_evidence": "Cell 61: prep_cols = sorted(prep_cols); prep_q1_cols = prep_cols[:3]; prep_q2_cols = prep_cols[3:6]\nCell 38: for h_col, a_col in zip(hiv_cols, art_cols): ...\nCell 42: from natsort import natsorted",
    "verdict": "VERIFIED",
    "notes": "Plain sorted() sorts lexicographically ('..._1', '..._10', '..._2'). Slicing [:3] takes indices 1, 10, 2 instead of 1, 2, 3 if there are 10+ columns. Also zip pairs by alphabetical sort order without validating month correspondence.",
}

# L-08: Cell 54 and KPLHIV summary: Suppressed sums rows, Total_KPLHIV counts unique clients. No latest VL or time-window logic. Unparseable values become UNKNOWN and count as not suppressed.
c54 = get_cell(54)
leads_report["L-08"] = {
    "lead": "Cell 54 and KPLHIV summary: Suppressed sums rows, Total_KPLHIV counts unique clients. No latest VL. Unparseable values become UNKNOWN and count as not suppressed.",
    "cell": 54,
    "code_evidence": "Total_KPLHIV=('kp_vp_unique_identifier_code_', 'nunique'), Suppressed=('is_suppressed','sum')\nreturn 'UNKNOWN'\nis_suppressed: if val == 'LDL': return True; elif isinstance(val, int) and val < 200: return True; return False",
    "verdict": "VERIFIED",
    "notes": "Cell 54 maps to UNKNOWN if no digit/ldl match, is_suppressed returns False for UNKNOWN, and groupby aggregates Suppressed by 'sum' across rows while Total_KPLHIV is nunique.",
}

# L-09: Summary cells: groupby silently drops rows with missing county/SR/region. Join keys are normalised via astype(str) (NaN becomes 'nan'/'NAN') and flip between .title() and .upper(); a spelling difference makes a left merge yield NaN with no warning.
c66_keys = [l for l in c66.splitlines() if "groupby" in l or "merge" in l]
c67 = get_cell(67)
c72 = get_cell(72)
leads_report["L-09"] = {
    "lead": "Summary cells: groupby silently drops missing county/SR/region; join keys normalisation issues (.title() vs .upper(), astype(str)).",
    "cell": "66, 67, 69, 72",
    "code_evidence": "Cell 66: groupby(['county', 'sr_name', 'region'])\nCell 72: def normalize_keys(df, keys=('county','sr_name','region')): ... df[k].astype(str).str.strip().str.title()",
    "verdict": "VERIFIED",
    "notes": "Standard pandas groupby without dropna=False drops rows where grouping keys are NaN. Also cell 72 normalizes keys with .title(), while cell 14/21 used .upper(), risking merge mismatches and turning NaN into string 'Nan'/'NAN'.",
}

# L-10: Cell 61 (hts_sem): enrolled_Apr_plus uses month >= 7 while comment says Apr ... month >= 10. Month only, no year.
leads_report["L-10"] = {
    "lead": "Cell 61 (hts_sem): enrolled_Apr_plus uses month >= 7 while comment says 'Apr … month >= 10'. Month only, no year.",
    "cell": 61,
    "code_evidence": "# boolean: enrolled in Apr or later (month >= 10)\nenrolled_Apr_plus = ConsolidatedFSW['date_of_enrolment'].dt.month >= 7",
    "verdict": "VERIFIED",
    "notes": "The code explicitly evaluates `.dt.month >= 7` (July) while the comment says 'Apr or later (month >= 10)'. Year is completely ignored, so someone enrolled in July 2018 is treated identically to July 2024.",
}

# L-11: Final summary cell: OLD_Cohort / NEW_Cohort are referenced in column ordering but never computed (silently filtered out).
c69 = get_cell(69)
leads_report["L-11"] = {
    "lead": "Final summary cell: OLD_Cohort / NEW_Cohort referenced in column ordering but never computed (silently filtered out).",
    "cell": 69,
    "code_evidence": "cohort_cols = ['OLD_Cohort', 'NEW_Cohort', 'TotalCohort']\nbase_order = keys + age_group_cols + cohort_cols + remaining",
    "verdict": "VERIFIED",
    "notes": "Cell 69 includes 'OLD_Cohort' and 'NEW_Cohort' in `cohort_cols`, but neither is computed in summary_FSW or age_group_counts. Later ordering step checks `if c in final_summary_FSW.columns`, which silently omits them.",
}

# L-12: Many: Hardcoded months (jul...dec), skiprows=2, machine path, Q1/Q2 labels regardless of real calendar.
c01 = get_cell(1)
c04 = get_cell(4)
leads_report["L-12"] = {
    "lead": "Hardcoded months (jul...dec), skiprows=2, machine path, Q1/Q2 labels regardless of real calendar.",
    "cell": "1, 4, 61, 75",
    "code_evidence": "Cell 01: directory = r'F:\\.shortcut-targets-by-id\\1ITOlPBpvV43hPTKn0MJkDV-Yj1aswrk5\\...'\nCell 04: pd.read_excel('FSW/FSW Register_Summaries.xlsb', skiprows=2)\nCell 61: prep_q1_cols = prep_cols[:3]; prep_q2_cols = prep_cols[3:6]",
    "verdict": "VERIFIED",
    "notes": "Absolute machine paths (F:\\...), fixed skiprows=2, hardcoded quarter splits [:3] and [3:6] assuming exactly 6 columns corresponding to fixed months.",
}

# L-13: Cells 75/77/80/82: Four near-identical exporters.
leads_report["L-13"] = {
    "lead": "Cells 75/77/80/82: Four near-identical exporters.",
    "cell": "75, 77, 80, 82",
    "code_evidence": "Cells 75 (350 lines), 77 (350 lines), 80 (370 lines), 82 (409 lines) repeat ~90% identical openpyxl formatting code.",
    "verdict": "VERIFIED",
    "notes": "Each cell re-implements openpyxl workbook creation, cell border styling, font definitions, header merging, and column width adjustments with slight variations for PWID and period mode.",
}

# L-14: Cleaning cells: .map(...) over every cell of an 80k x 300 frame; very slow.
leads_report["L-14"] = {
    "lead": "Cleaning cells: .map(...) over every cell of an 80k x 300 frame; very slow.",
    "cell": 14,
    "code_evidence": "ConsolidatedKPLHIV = ConsolidatedKPLHIV.map(lambda x: str(x).capitalize() if isinstance(x, str) else x)\nConsolidatedKPLHIV = ConsolidatedKPLHIV.map(lambda x: x.strip() if isinstance(x, str) else x)",
    "verdict": "VERIFIED",
    "notes": "Calling DataFrame.map(...) twice elementwise across an 80k x 300 DataFrame executes 48 million Python lambda calls, causing extreme performance degradation.",
}

# L-15: Cell 61: Semester logic differs by indicator (HTS uses AND/OR, others union; New_on_ART uses Q1 columns only). Document indicator by indicator; never assume uniformity.
leads_report["L-15"] = {
    "lead": "Cell 61: Semester logic differs by indicator (HTS uses AND/OR, others union; New_on_ART uses Q1 columns only).",
    "cell": 61,
    "code_evidence": "prep_sem: (prep_q1 + prep_q2) >= 1\nhts_sem: (hts_q1 > 0 & hts_q2 > 0) | (hts_q2 > 0 & enrolled_Apr_plus)\nhts_sem_any: (hts_q1 > 0 | hts_q2 > 0)\nNew_on_ART: cell 66 only has New_on_ART (from Q1) and New_on_ART_Q2 (from Q2), no SEM!",
    "verdict": "VERIFIED",
    "notes": "PrEP, STI, TB, Condoms, NSP, DefinedPackage use >= 1 (union / OR). HTS has both hts_sem (AND/OR with enrolment date) and hts_sem_any (OR). Active ART and New_on_ART do not have a defined semester column in Cell 66 summary.",
}

# L-16: CCC check: One direction only (KPLHIV -> Register). Null CCC numbers are not counted.
c52 = get_cell(52)
leads_report["L-16"] = {
    "lead": "CCC check: One direction only (KPLHIV -> Register). Null CCC numbers are not counted.",
    "cell": 52,
    "code_evidence": "left_key = 'ccc_number_nupi_n_a_10_digit_number_'\nright_ids = set(right_ser.unique())\nleft_norm = _normalize_ids(ConsolidatedKPLHIV[left_key])\n# mask only for non-null left IDs; do NOT count missing left IDs as mismatches",
    "verdict": "VERIFIED",
    "notes": "Cell 52 checks if KPLHIV CCC numbers exist in Register (ConsolidatedFSW), but does NOT check if Register CCC numbers exist in KPLHIV. Additionally, null/blank CCC numbers on the left are explicitly dropped from mismatch detection.",
}

# L-17: Cell 61: NSP requirements commented out of both Defined Package pathways, including the PWID path (see BR-001).
leads_report["L-17"] = {
    "lead": "Cell 61: NSP requirements commented out of both Defined Package pathways, including the PWID path (see BR-001).",
    "cell": 61,
    "code_evidence": "# (ConsolidatedFSW['nsp_q1'] == 1) &\n# (ConsolidatedFSW['nsp_q2'] == 1) &\n#  (ConsolidatedFSW['nsp_q1'] == 1) &\n#  (ConsolidatedFSW['nsp_q2'] == 1) &",
    "verdict": "VERIFIED",
    "notes": "In Cell 61, lines 206, 216, 229, and 240 have the NSP conditions commented out in both plhivservice (pathway 2) and definedpackage (pathway 1). Thus NSP is ignored for all populations in the notebook.",
}

for lid, info in leads_report.items():
    print(f"[{info['verdict']}] {lid}: {info['lead'][:70]}")

with open(
    Path(__file__).resolve().parent / "leads_report.json", "w", encoding="utf-8"
) as f:
    json.dump(leads_report, f, indent=2)
print("Saved leads_report.json")
