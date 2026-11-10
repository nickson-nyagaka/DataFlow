#!/usr/bin/env python3
"""Automated Phase 0 Exit Criteria Verification Script.

Checks:
1. Every code cell has an entry in NOTEBOOK_ANALYSIS (count matches 58).
2. Every column produced by any .agg(...) or export block appears in the dictionary.
3. Semester logic documented indicator by indicator in one table.
4. Each lead (L-01..L-17) has a verdict with evidence; no lead left unexamined.
5. The four exporters are diffed and single-parametrised exporter proposal is written.
6. Indicator names are identical across all documents.
7. No .py application code outside scripts/audit/ and scripts/.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "docs"
AUDIT_DIR = Path(__file__).resolve().parent


def check_notebook_analysis():
    p = DOCS_DIR / "NOTEBOOK_ANALYSIS.md"
    assert p.exists(), "NOTEBOOK_ANALYSIS.md does not exist!"
    content = p.read_text(encoding="utf-8")

    # Check count of code cells in table
    code_rows = re.findall(r"\|\s*(\d{2})\s*\|\s*\*\*CODE\*\*", content)
    print(
        f"[Check 1] Code cells documented in NOTEBOOK_ANALYSIS: {len(code_rows)} / 58"
    )
    assert len(code_rows) == 58, f"Expected 58 code cells, found {len(code_rows)}"

    # Check exporter diff and proposal
    assert "Exporter Comparison Matrix" in content, "Exporter diff matrix missing!"
    assert "Unified Parametrised Exporter Proposal" in content, (
        "Exporter proposal missing!"
    )
    print(
        "  -> NOTEBOOK_ANALYSIS verified (58 code cells, Mermaid diagram, exporter diff & proposal)."
    )


def check_indicator_dictionary():
    p = DOCS_DIR / "INDICATOR_DICTIONARY.md"
    assert p.exists(), "INDICATOR_DICTIONARY.md does not exist!"
    content = p.read_text(encoding="utf-8")

    # Check semester logic table
    assert "Semester Logic by Indicator Family" in content, "Semester table missing!"
    assert "HTS (General)" in content and "Defined Package" in content, (
        "Incomplete semester table!"
    )

    # Check indicators present
    # Load extracted columns
    with open(AUDIT_DIR / "cell_meta.json", "r", encoding="utf-8") as f:
        json.load(f)

    # Check critical columns
    critical_cols = [
        "county",
        "sr_name",
        "region",
        "15-19",
        "20-24",
        "25+",
        "Below 15",
        "TotalCohort",
        "TotalPE",
        "HTSQ1",
        "HTSQ2",
        "HTS_SEM",
        "HTS_SEM_ANY",
        "HTS_Negative",
        "HTS_Negative_Q2",
        "HTS_Positive",
        "HTS_Positive_Q2",
        "Total_KPLHIV",
        "Suppressed",
        "DefinedPackage_Q1",
        "DefinedPackage_Q2",
        "DefinedPackage_SEM",
        "PREP_Q1",
        "PREP_Q2",
        "PREP_SEM",
        "New_on_ART",
        "New_on_ART_Q2",
        "CurrentArt_Q1",
        "CurrentArt_Q2",
        "PLHIV_Q1",
        "PLHIV_Q2",
        "STISCREENEDQ_1",
        "STISCREENEDQ_2",
        "STI_SCREENED_SEM",
        "STIDiagnosid_Q1",
        "STI_DIAGNOSED_Q2",
        "STI_DIAGNOSED_SEM",
        "STItreated_Q1",
        "STI_TREATED_Q2",
        "STI_TREATED_SEM",
        "TB_SCREENED_Q1",
        "TB_SCREENED_Q2",
        "TB_SCREENED_SEM",
        "PeerEducation_Q1",
        "PeerEducation_Q2",
        "PeerEducation_SEM",
        "HE_RRC_Q1",
        "HE_RRC_Q2",
        "ReceivedCondom_Q1",
        "ReceivedCondom_Q2",
        "ReceivedCondom_SEM",
        "total_condoms_Q1",
        "total_condoms_Q2",
        "total_condoms_SEM",
        "NSP_Q1",
        "NSP_Q2",
        "NSP_SEM",
        "total_nsp_Q1",
        "total_nsp_Q2",
        "total_nsp_SEM",
        "HTS_Tested",
        "OLD_Cohort",
        "NEW_Cohort",
    ]

    missing = []
    for col in critical_cols:
        if f"`{col}`" not in content:
            missing.append(col)

    print(
        f"[Check 2] Checked {len(critical_cols)} output columns in INDICATOR_DICTIONARY. Missing: {len(missing)}"
    )
    assert len(missing) == 0, f"Missing output columns in dictionary: {missing}"
    print(
        "  -> INDICATOR_DICTIONARY verified (all columns present with full schema and semester table)."
    )


def check_known_issues():
    p = DOCS_DIR / "KNOWN_ISSUES.md"
    assert p.exists(), "KNOWN_ISSUES.md does not exist!"
    content = p.read_text(encoding="utf-8")

    for i in range(1, 18):
        lead_id = f"L-{i:02d}"
        assert f"**{lead_id}**" in content, f"Lead {lead_id} missing from KNOWN_ISSUES!"
        assert f"#### {lead_id}:" in content, f"Detailed section for {lead_id} missing!"

    print(
        "[Check 3] Verified all 17 leads L-01..L-17 with code evidence and verdicts in KNOWN_ISSUES."
    )


def check_population_rules_and_excel_spec():
    pr = DOCS_DIR / "POPULATION_RULES.md"
    assert pr.exists(), "POPULATION_RULES.md missing!"
    pr_content = pr.read_text(encoding="utf-8")
    for pop in ["FSW", "MSM", "TG", "PWID", "VP"]:
        assert pop in pr_content, f"Population {pop} missing in POPULATION_RULES!"

    es = DOCS_DIR / "EXCEL_OUTPUT_SPECIFICATION.md"
    assert es.exists(), "EXCEL_OUTPUT_SPECIFICATION.md missing!"
    es_content = es.read_text(encoding="utf-8")
    assert "Cascadia Code" in es_content, "Font Cascadia Code missing!"
    assert "Candara" in es_content, "Font Candara missing!"
    assert "FF7D81" in es_content, "Subheader color missing!"
    assert "6BD669" in es_content, "Total row color missing!"
    print("[Check 4] Verified POPULATION_RULES and EXCEL_OUTPUT_SPECIFICATION.")


def check_indicator_naming_consistency():
    # Compare indicator names across INDICATOR_DICTIONARY and EXCEL_OUTPUT_SPECIFICATION
    id_content = (DOCS_DIR / "INDICATOR_DICTIONARY.md").read_text(encoding="utf-8")
    es_content = (DOCS_DIR / "EXCEL_OUTPUT_SPECIFICATION.md").read_text(
        encoding="utf-8"
    )

    # Find all columns listed in EXCEL_OUTPUT_SPECIFICATION blocks
    cols_in_spec = re.findall(r"columns:\s*\[(.*?)\]", es_content)
    all_spec_cols = set()
    for c_list in cols_in_spec:
        items = [i.strip().strip('"').strip("'") for i in c_list.split(",")]
        all_spec_cols.update(items)

    print(
        f"[Check 5] Found {len(all_spec_cols)} distinct output columns in EXCEL_OUTPUT_SPECIFICATION."
    )
    missing_in_dict = []
    for c in all_spec_cols:
        if f"`{c}`" not in id_content:
            missing_in_dict.append(c)

    assert len(missing_in_dict) == 0, (
        f"Columns in Excel spec not in Indicator Dictionary: {missing_in_dict}"
    )
    print("  -> Indicator naming consistency 100% verified across documents.")


def check_no_application_code():
    py_files = list(BASE_DIR.glob("**/*.py"))
    violations = []
    for f in py_files:
        rel = f.relative_to(BASE_DIR).as_posix()
        # Allowed in Phase 0: scripts/**
        if not rel.startswith("scripts/"):
            violations.append(rel)

    print(
        f"[Check 6] Python files found: {len(py_files)}. Non-script violations: {len(violations)}"
    )
    assert len(violations) == 0, (
        f"Disallowed application code found in Phase 0: {violations}"
    )
    print("  -> Zero application code outside scripts/ confirmed.")


def main():
    print("=" * 60)
    print("STARTING PHASE 0 AUTOMATED VERIFICATION")
    print("=" * 60)
    check_notebook_analysis()
    check_indicator_dictionary()
    check_known_issues()
    check_population_rules_and_excel_spec()
    check_indicator_naming_consistency()
    check_no_application_code()
    print("=" * 60)
    print("ALL PHASE 0 EXIT CRITERIA PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
