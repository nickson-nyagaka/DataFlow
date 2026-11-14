"""Permanent integration and regression test suite for Transgender (TG) dataset.

Validates:
1. Ingestion and data integrity (zero records dropped, 100% row preservation).
2. DQA accuracy (zero false positives on dates, exact detection of 5 genuine exceptions).
3. Service Summary reconciliation against legacy reference (100% concordance across 16 counties x 25 columns).
4. KPI Demographic summary reconciliation against legacy reference (100% concordance across 16 counties x 24 columns).
5. Population-specific Defined Package rules (no NSP required for TG, dual clinical pathways verified).
6. Unique-client counting semantics.
7. Excel export package structure and formula integrity.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from analytics.demographics import compute_kpi_demographic_summary
from analytics.engine import run_analytics
from core.cleaning import clean_kplhiv_frame, clean_register_frame
from core.config_models import load_population_config
from core.ingestion import ingest_workbook
from core.runner import run_full_pipeline
from core.validation import run_dqa
from reporting.package_builder import build_export_summary

RAW_TG_PATH = Path("reference/Consolidated TG.xlsb")
LEGACY_SUMMARY_PATH = Path("reference/Summary TG.xlsx")


@pytest.fixture(scope="module")
def tg_datasets():
    """Loads and cleans raw TG dataset once for module tests."""
    assert RAW_TG_PATH.exists(), f"Reference file missing: {RAW_TG_PATH}"
    assert LEGACY_SUMMARY_PATH.exists(), f"Legacy summary missing: {LEGACY_SUMMARY_PATH}"

    pop_config = load_population_config("TG")
    reg_raw, kp_raw, audit = ingest_workbook(RAW_TG_PATH, pop_config)
    reg_clean = clean_register_frame(reg_raw)
    kp_clean = clean_kplhiv_frame(kp_raw)

    return {
        "reg_raw": reg_raw,
        "kp_raw": kp_raw,
        "reg_clean": reg_clean,
        "kp_clean": kp_clean,
        "audit": audit,
    }


def test_tg_data_integrity(tg_datasets):
    """Verifies that ingestion and cleaning do not silently alter or drop records."""
    reg_raw = tg_datasets["reg_raw"]
    kp_raw = tg_datasets["kp_raw"]
    reg_clean = tg_datasets["reg_clean"]
    kp_clean = tg_datasets["kp_clean"]

    # 1. Row counts exactly preserved
    assert len(reg_raw) == 3124
    assert len(reg_clean) == 3124
    assert len(kp_raw) == 100
    assert len(kp_clean) == 100

    # 2. UIC counts
    assert reg_clean["kp_vp_unique_identifier_code"].nunique() == 3124
    assert reg_clean["kp_vp_unique_identifier_code"].isna().sum() == 0
    assert kp_clean["kp_vp_unique_identifier_code"].nunique() == 100

    # 3. Clean date parsing (0 false missing dates)
    assert reg_clean["date_of_enrolment"].isna().sum() == 0
    assert reg_clean["date_of_birth_dd_mm_yyyy_"].isna().sum() == 0

    # 4. Mandatory demographic completeness
    assert reg_clean["county"].isna().sum() == 0
    assert reg_clean["sr_name"].isna().sum() == 0
    assert reg_clean["region"].isna().sum() == 0
    assert reg_clean["age"].isna().sum() == 0
    assert reg_clean["sex_m_f_"].isna().sum() == 0


def test_tg_dqa_accuracy(tg_datasets):
    """Verifies DQA engine accuracy: zero false positives and exactly 5 genuine exceptions."""
    reg_clean = tg_datasets["reg_clean"]
    kp_clean = tg_datasets["kp_clean"]

    dqa_res = run_dqa(reg_clean, kp_clean, population="TG", block_on_critical=False)

    # Assert exactly 5 exceptions total
    assert dqa_res.total_exceptions == 5
    assert dqa_res.get_critical_counts() == {"hiv_neg_on_art": 3}
    assert dqa_res.severity_counts == {"Critical": 3, "Major": 2}
    assert dqa_res.rule_counts == {
        "hiv_neg_on_art": 3,
        "hiv_pos_no_art": 2,
    }

    # Verify zero false positives for date fields
    assert "missing_enrolment_date" not in dqa_res.rule_counts
    assert "missing_dob" not in dqa_res.rule_counts
    assert "duplicate_uic" not in dqa_res.rule_counts
    assert "missing_uic" not in dqa_res.rule_counts


def test_tg_defined_package_rules(tg_datasets):
    """Verifies TG population-specific Defined Package rules (no NSP required, dual pathways)."""
    reg_clean = tg_datasets["reg_clean"]
    kp_clean = tg_datasets["kp_clean"]

    res = run_analytics(reg_clean, kp_clean, population="TG")
    reg = res["cleaned_register"]

    # 1. Total Defined Package Q1 must be exactly 3,051 clients
    assert reg["definedpackage_q1"].sum() == 3051

    # 2. General pathway: 2,965 clients
    general_pathway = (
        (reg["hts_q1"] == 1)
        & (reg["sti_screened_q1"] == 1)
        & (reg["tb_screened_q1"] == 1)
        & (reg["condoms_q1"] == 1)
        & (reg["he_rrc_q1"] == 1)
    )
    assert general_pathway.sum() == 2965

    # 3. PLHIV service pathway: 86 clients
    assert reg["plhivservice_q1"].sum() == 86

    # 4. Total unique sum
    assert (general_pathway | (reg["plhivservice_q1"] == 1)).sum() == 3051


def test_tg_service_summary_reconciliation(tg_datasets):
    """Reconciles 100% of cells in DataFlow Service Summary against legacy TG sheet."""
    reg_clean = tg_datasets["reg_clean"]
    kp_clean = tg_datasets["kp_clean"]

    analytics_dict = run_analytics(reg_clean, kp_clean, population="TG")
    summary_df = build_export_summary(
        cleaned_register=analytics_dict["cleaned_register"],
        cleaned_kplhiv=analytics_dict["cleaned_kplhiv"],
        population="TG",
        period_mode="Q1",
    )

    wb_leg = openpyxl.load_workbook(LEGACY_SUMMARY_PATH, data_only=True)
    ws_tg = wb_leg["TG"]

    col_map = [
        ("county", 0),
        ("sr_name", 1),
        ("region", 2),
        ("15-19", 3),
        ("20-24", 4),
        ("25+", 5),
        ("Below 15", 6),
        ("TotalCohort", 7),
        ("TotalPE", 8),
        ("HTSQ1", 9),
        ("HTS_Negative", 10),
        ("HTS_Positive", 11),
        ("Total_KPLHIV", 12),
        ("Suppressed", 13),
        ("DefinedPackage_Q1", 14),
        ("PREP_Q1", 15),
        ("New_on_ART", 16),
        ("CurrentArt_Q1", 17),
        ("STISCREENEDQ_1", 18),
        ("STIDiagnosid_Q1", 19),
        ("STItreated_Q1", 20),
        ("TB_SCREENED_Q1", 21),
        ("PeerEducation_Q1", 22),
        ("ReceivedCondom_Q1", 23),
        ("total_condoms_Q1", 24),
    ]

    leg_rows = []
    for r in range(3, 19):
        leg_rows.append([ws_tg.cell(r, c).value for c in range(1, 26)])
    df_leg = pd.DataFrame(leg_rows)

    summary_df["key"] = summary_df["county"].str.upper() + "_" + summary_df["sr_name"].str.upper()
    df_leg["key"] = df_leg[0].astype(str).str.upper() + "_" + df_leg[1].astype(str).str.upper()

    merged = pd.merge(summary_df, df_leg, on="key")
    assert len(merged) == 16, "Failed to match all 16 reporting counties"

    diffs = []
    for _, row in merged.iterrows():
        key = row["key"]
        for df_col, leg_idx in col_map:
            if leg_idx in (0, 1, 2):
                assert str(row[df_col]).upper().strip() == str(row[leg_idx]).upper().strip()
            else:
                v_df = float(row[df_col] if pd.notna(row[df_col]) else 0)
                v_leg = float(row[leg_idx] if (row[leg_idx] is not None and pd.notna(row[leg_idx])) else 0)
                if v_df != v_leg:
                    diffs.append((key, df_col, v_leg, v_df))

    assert len(diffs) == 0, f"Found {len(diffs)} Service Summary cell discrepancies: {diffs}"


def test_tg_kpi_demographic_reconciliation(tg_datasets):
    """Reconciles 100% of cells in DataFlow KPI summary against legacy KPI sheet."""
    reg_clean = tg_datasets["reg_clean"]
    kp_clean = tg_datasets["kp_clean"]

    res = run_analytics(reg_clean, kp_clean, population="TG")
    kpi_df = compute_kpi_demographic_summary(res["cleaned_register"], period_mode="Q1")

    wb_leg = openpyxl.load_workbook(LEGACY_SUMMARY_PATH, data_only=True)
    ws_kpi = wb_leg["KPI"]

    leg_kpi_rows = []
    for r in range(3, 19):
        leg_kpi_rows.append([ws_kpi.cell(r, c).value for c in range(1, 25)])
    df_leg_kpi = pd.DataFrame(leg_kpi_rows)

    kpi_df["key"] = kpi_df["sr_name"] + "_" + kpi_df["region"] + "_" + kpi_df["county"]
    df_leg_kpi["key"] = (
        df_leg_kpi[0].astype(str).str.upper()
        + "_"
        + df_leg_kpi[1].astype(str).str.upper()
        + "_"
        + df_leg_kpi[2].astype(str).str.upper()
    )

    merged = pd.merge(kpi_df, df_leg_kpi, on="key")
    assert len(merged) == 16, "Failed to match all 16 KPI reporting rows"

    kpi_num_cols = [c for c in kpi_df.columns if c not in ("sr_name", "region", "county", "key")]
    diffs = []
    for _, row in merged.iterrows():
        key = row["key"]
        for c in range(3, 24):
            v_df = float(row[kpi_num_cols[c - 3]])
            v_leg = float(row[c])
            if v_df != v_leg:
                diffs.append((key, kpi_num_cols[c - 3], v_leg, v_df))

    assert len(diffs) == 0, f"Found {len(diffs)} KPI cell discrepancies: {diffs}"


def test_tg_pipeline_exports_and_parity(tmp_path: Path):
    """Tests that full pipeline generates compliant export workbooks matching legacy benchmark."""
    res = run_full_pipeline(
        file_source=RAW_TG_PATH,
        file_name="Consolidated TG.xlsb",
        population="TG",
        period_mode="Q1",
        force_rerun=True,
    )

    assert res.total_cohort == 3124
    assert res.total_dqa_exceptions == 5
    assert res.critical_dqa_count == 3
    assert res.major_dqa_count == 2

    # Verify export files exist
    assert res.package_paths["master_workbook"].exists()
    assert res.package_paths["summary_workbook"].exists()
    assert res.package_paths["disaggregation_workbook"].exists()
    assert res.package_paths["zip_package"].exists()

    # Verify Master workbook contains KPI tab and excludes Run Metadata & Cleaning Log
    wb_master = openpyxl.load_workbook(res.package_paths["master_workbook"], data_only=True)
    assert "KPI" in wb_master.sheetnames
    assert "KP_Summary" in wb_master.sheetnames
    assert "Run Metadata" not in wb_master.sheetnames
    assert "Cleaning Log" not in wb_master.sheetnames
