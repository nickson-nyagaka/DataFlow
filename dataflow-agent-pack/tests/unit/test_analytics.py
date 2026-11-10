"""Comprehensive unit tests for the DATAFLOW Analytical Engine (Phase 4).

Covers:
- Stage A: 100% bit-for-bit oracle parity across all 5 populations (FSW, PWID, MSM, TG, VP).
- Stage B: Isolated switch-flipping tests for each bug-compatibility switch.
- Defined Package matrix tests across 5 populations x components x pathways x periods x multi-row UIC.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from janitor import clean_names

from analytics.defined_package import compute_defined_package_indicators
from analytics.demographics import compute_age_group_counts
from analytics.engine import run_analytics
from core.compat import CompatSwitches
from core.config_models import load_population_config
from oracle.runner import run_oracle, run_oracle_from_dfs
from tests.synthetic.generator import generate_synthetic_data

FIXTURES_DIR = Path("tests/synthetic/fixtures")


# ==============================================================================
# STAGE A: 100% BIT-FOR-BIT ORACLE PARITY
# ==============================================================================


@pytest.mark.parametrize(
    "population,fixture_file",
    [
        ("FSW", FIXTURES_DIR / "synthetic_fsw.xlsx"),
        ("PWID", FIXTURES_DIR / "synthetic_pwid.xlsx"),
    ],
)
def test_stage_a_oracle_parity_from_fixtures(population: str, fixture_file: Path):
    """Verifies 100% parity against legacy oracle on persisted synthetic fixtures."""
    oracle_res = run_oracle(fixture_file, population=population)
    oracle_df = oracle_res["final_summary"]

    reg_df = clean_names(
        pd.read_excel(fixture_file, skiprows=2, sheet_name="Register", engine="calamine")
    )
    kp_df = clean_names(
        pd.read_excel(fixture_file, skiprows=2, sheet_name="KPLHIV", engine="calamine")
    )

    engine_res = run_analytics(
        reg_df, kp_df, population=population, compat=CompatSwitches.all_enabled()
    )
    engine_df = engine_res["final_summary"]

    assert oracle_df.shape == engine_df.shape
    diff_cols = []
    for col in oracle_df.columns:
        o_s = oracle_df[col].fillna(0)
        e_s = engine_df[col].fillna(0)
        if not (o_s == e_s).all():
            diff_cols.append(col)

    assert diff_cols == [], f"Parity mismatch in {population} on columns: {diff_cols}"


@pytest.mark.parametrize("population", ["MSM", "TG", "VP"])
def test_stage_a_oracle_parity_generated_populations(population: str):
    """Verifies 100% parity against legacy oracle across generated populations."""
    reg_df, kp_df, _ = generate_synthetic_data(population=population, num_clients=60, seed=42)

    oracle_res = run_oracle_from_dfs(reg_df, kp_df, population=population)
    oracle_df = oracle_res["final_summary"]

    engine_res = run_analytics(
        reg_df, kp_df, population=population, compat=CompatSwitches.all_enabled()
    )
    engine_df = engine_res["final_summary"]

    assert oracle_df.shape == engine_df.shape
    diff_cols = []
    for col in oracle_df.columns:
        o_s = oracle_df[col].fillna(0)
        e_s = engine_df[col].fillna(0)
        if not (o_s == e_s).all():
            diff_cols.append(col)

    assert diff_cols == [], f"Parity mismatch in {population} on columns: {diff_cols}"


# ==============================================================================
# STAGE B: SWITCH-FLIPPING TESTS
# ==============================================================================


def test_switch_legacy_missing_age_below_15():
    """D-021: Switch ON counts missing age in 'Below 15'; switch OFF counts in 'Unknown'."""
    df = pd.DataFrame(
        {
            "county": ["NAIROBI", "NAIROBI"],
            "sr_name": ["SR1", "SR1"],
            "region": ["NRR", "NRR"],
            "age": [np.nan, 22],
        }
    )

    # Legacy switch ON
    counts_legacy = compute_age_group_counts(df, compat=CompatSwitches.all_enabled()).set_index(
        ["county", "sr_name", "region"]
    )
    below_15_legacy = (
        counts_legacy["Below 15"]
        if "Below 15" in counts_legacy.columns
        else pd.Series(0, index=counts_legacy.index)
    )
    assert below_15_legacy.loc[("NAIROBI", "SR1", "NRR")] == 1
    assert "Unknown" not in counts_legacy.columns

    # Modern switch OFF
    counts_modern = compute_age_group_counts(df, compat=CompatSwitches.all_disabled()).set_index(
        ["county", "sr_name", "region"]
    )
    below_15_modern = (
        counts_modern["Below 15"]
        if "Below 15" in counts_modern.columns
        else pd.Series(0, index=counts_modern.index)
    )
    assert below_15_modern.loc[("NAIROBI", "SR1", "NRR")] == 0
    assert counts_modern.loc[("NAIROBI", "SR1", "NRR"), "Unknown"] == 1


def test_switch_legacy_row_sum_flags():
    """L-01 / D-027: Switch ON does row-level sum (double-counts encounters); switch OFF counts unique clients."""
    reg_df = pd.DataFrame(
        {
            "county": ["MOMBASA", "MOMBASA"],
            "sr_name": ["SR1", "SR1"],
            "region": ["COAST", "COAST"],
            "kp_vp_unique_identifier_code": ["U100", "U100"],  # Same client, 2 encounters
            "peer_educator_code": ["PE1", "PE1"],
            "prep_status_1": ["Refill", "Refill"],
            "prep_status_2": ["None", "None"],
            "prep_status_3": ["None", "None"],
            "prep_status_4": ["None", "None"],
            "prep_status_5": ["None", "None"],
            "prep_status_6": ["None", "None"],
        }
    )

    # Switch ON: 2 rows -> PREP_Q1 = 2
    res_legacy = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_enabled())[
        "summary_register"
    ]
    assert res_legacy.loc[0, "PREP_Q1"] == 2
    assert res_legacy.loc[0, "TotalCohort"] == 1

    # Switch OFF: 1 unique client -> PREP_Q1 = 1
    res_modern = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_disabled())[
        "summary_register"
    ]
    assert res_modern.loc[0, "PREP_Q1"] == 1
    assert res_modern.loc[0, "TotalCohort"] == 1


def test_switch_legacy_hts_sem_month_ge_7():
    """D-024 (OQ-06): Switch ON requires tested in both Q1&Q2 or enrolled July+; switch OFF allows any test."""
    # Client enrolled in Feb (month 2), tested only in Q2 (Visit 4)
    reg_df = pd.DataFrame(
        {
            "county": ["KISUMU"],
            "sr_name": ["SR1"],
            "region": ["WESTERN"],
            "kp_vp_unique_identifier_code": ["K100"],
            "date_of_enrolment": ["2024-02-10"],
            "hiv_tested_results_p_n_nd_na_1": ["None"],
            "hiv_tested_results_p_n_nd_na_2": ["None"],
            "hiv_tested_results_p_n_nd_na_3": ["None"],
            "hiv_tested_results_p_n_nd_na_4": ["Negative"],
            "hiv_tested_results_p_n_nd_na_5": ["None"],
            "hiv_tested_results_p_n_nd_na_6": ["None"],
        }
    )

    # Legacy: excluded from hts_sem because enrolled before July and missed Q1
    res_legacy = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_enabled())[
        "cleaned_register"
    ]
    assert res_legacy.loc[0, "hts_q1"] == 0
    assert res_legacy.loc[0, "hts_q2"] == 1
    assert res_legacy.loc[0, "hts_sem"] == 0

    # Modern: counted in hts_sem because tested in semester
    res_modern = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_disabled())[
        "cleaned_register"
    ]
    assert res_modern.loc[0, "hts_q1"] == 0
    assert res_modern.loc[0, "hts_q2"] == 1
    assert res_modern.loc[0, "hts_sem"] == 1


def test_switch_legacy_comment_out_pwid_nsp():
    """D-001 / D-020: Switch ON ignores NSP for PWID; switch OFF enforces NSP."""
    cfg = load_population_config("PWID")
    df = pd.DataFrame(
        {
            "kp_vp_unique_identifier_code": ["P100"],
            "hts_q1": [1],
            "sti_screened_q1": [1],
            "tb_screened_q1": [1],
            "condoms_q1": [1],
            "he_rrc_q1": [1],
            "nsp_q1": [0],  # No NSP received
            "plhiv": [0],
            "hts_q2": [0],
            "sti_screened_q2": [0],
            "tb_screened_q2": [0],
            "condoms_q2": [0],
            "he_rrc_q2": [0],
            "nsp_q2": [0],
            "plhiv_q2": [0],
        }
    )

    # Legacy switch ON (commented out): Defined package is achieved without NSP
    res_legacy = compute_defined_package_indicators(df, cfg, compat=CompatSwitches.all_enabled())
    assert res_legacy.loc[0, "definedpackage_q1"] == 1

    # Modern switch OFF: Defined package is NOT achieved because NSP is missing
    res_modern = compute_defined_package_indicators(df, cfg, compat=CompatSwitches.all_disabled())
    assert res_modern.loc[0, "definedpackage_q1"] == 0


def test_switch_legacy_capitalize_vocabulary():
    """D-008: Switch ON fails on 'Known Positive'; switch OFF matches case-insensitively."""
    reg_df = pd.DataFrame(
        {
            "county": ["MOMBASA"],
            "sr_name": ["SR1"],
            "region": ["COAST"],
            "kp_vp_unique_identifier_code": ["U100"],
            "hiv_tested_results_p_n_nd_na_1": ["Known Positive"],  # Mixed case
            "hiv_tested_results_p_n_nd_na_2": ["None"],
            "hiv_tested_results_p_n_nd_na_3": ["None"],
            "hiv_tested_results_p_n_nd_na_4": ["None"],
            "hiv_tested_results_p_n_nd_na_5": ["None"],
            "hiv_tested_results_p_n_nd_na_6": ["None"],
        }
    )

    # Legacy switch ON: plhiv is 0
    res_legacy = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_enabled())[
        "cleaned_register"
    ]
    assert res_legacy.loc[0, "plhiv"] == 0

    # Modern switch OFF: plhiv is 1
    res_modern = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_disabled())[
        "cleaned_register"
    ]
    assert res_modern.loc[0, "plhiv"] == 1


def test_switch_legacy_lexicographic_column_sort():
    """L-07: Switch ON pulls visit 10 into Q1; switch OFF sorts naturally by visit index."""
    reg_df = pd.DataFrame(
        {
            "county": ["NAIROBI"],
            "sr_name": ["SR1"],
            "region": ["NRR"],
            "kp_vp_unique_identifier_code": ["U100"],
        }
    )
    # Populate visit columns 1 through 10
    # Visit 10 has 100 condoms; visits 1-3 have 0 condoms; visit 4 has 50 condoms
    for v in range(1, 11):
        reg_df[f"condoms_distributed_indicate_number_n_a_for_inmates_{v}"] = 0
    reg_df["condoms_distributed_indicate_number_n_a_for_inmates_10"] = 100
    reg_df["condoms_distributed_indicate_number_n_a_for_inmates_4"] = 50

    # Switch ON: Q1 grabs [col_1, col_10, col_2], so total_condoms_q1 == 100
    res_legacy = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_enabled())[
        "cleaned_register"
    ]
    assert res_legacy.loc[0, "total_condoms_q1"] == 100

    # Switch OFF: Q1 grabs [col_1, col_2, col_3], so total_condoms_q1 == 0, and Q2 grabs [col_4, col_5, col_6] == 50
    res_modern = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_disabled())[
        "cleaned_register"
    ]
    assert res_modern.loc[0, "total_condoms_q1"] == 0
    assert res_modern.loc[0, "total_condoms_q2"] == 50


# ==============================================================================
# DEFINED PACKAGE MATRIX TESTS
# ==============================================================================


@pytest.mark.parametrize("pop", ["FSW", "MSM", "PWID", "TG", "VP"])
def test_defined_package_all_components_present_general_pathway(pop: str):
    """Client receiving all required services achieves defined package in modern mode."""
    cfg = load_population_config(pop)
    is_pwid = pop == "PWID"
    df = pd.DataFrame(
        {
            "kp_vp_unique_identifier_code": ["U1"],
            "hts_q1": [1],
            "sti_screened_q1": [1],
            "tb_screened_q1": [1],
            "condoms_q1": [1],
            "he_rrc_q1": [1],
            "nsp_q1": [1 if is_pwid else 0],
            "plhiv": [0],
            "hts_q2": [1],
            "sti_screened_q2": [1],
            "tb_screened_q2": [1],
            "condoms_q2": [1],
            "he_rrc_q2": [1],
            "nsp_q2": [1 if is_pwid else 0],
            "plhiv_q2": [0],
        }
    )
    res = compute_defined_package_indicators(df, cfg, compat=CompatSwitches.all_disabled())
    assert res.loc[0, "definedpackage_q1"] == 1
    assert res.loc[0, "definedpackage_q2"] == 1
    assert res.loc[0, "definedpackage_sem"] == 1


@pytest.mark.parametrize(
    "missing_component", ["hts_q1", "sti_screened_q1", "tb_screened_q1", "condoms_q1", "he_rrc_q1"]
)
def test_defined_package_general_pathway_missing_single_component(missing_component: str):
    """Omitting any single component disqualifies client from general defined package."""
    cfg = load_population_config("FSW")
    row = {
        "kp_vp_unique_identifier_code": ["U1"],
        "hts_q1": [1],
        "sti_screened_q1": [1],
        "tb_screened_q1": [1],
        "condoms_q1": [1],
        "he_rrc_q1": [1],
        "nsp_q1": [0],
        "plhiv": [0],
        "hts_q2": [0],
        "sti_screened_q2": [0],
        "tb_screened_q2": [0],
        "condoms_q2": [0],
        "he_rrc_q2": [0],
        "nsp_q2": [0],
        "plhiv_q2": [0],
    }
    row[missing_component] = [0]
    df = pd.DataFrame(row)
    res = compute_defined_package_indicators(df, cfg, compat=CompatSwitches.all_disabled())
    assert res.loc[0, "definedpackage_q1"] == 0


def test_defined_package_plhiv_service_pathway_without_hts():
    """Known positive client does NOT require HTS to achieve Defined Package via PLHIV service."""
    cfg = load_population_config("FSW")
    df = pd.DataFrame(
        {
            "kp_vp_unique_identifier_code": ["U1"],
            "hts_q1": [0],  # No HTS test
            "plhiv": [1],  # Known positive
            "sti_screened_q1": [1],
            "tb_screened_q1": [1],
            "condoms_q1": [1],
            "he_rrc_q1": [1],
            "nsp_q1": [0],
            "hts_q2": [0],
            "sti_screened_q2": [0],
            "tb_screened_q2": [0],
            "condoms_q2": [0],
            "he_rrc_q2": [0],
            "nsp_q2": [0],
            "plhiv_q2": [0],
        }
    )
    res = compute_defined_package_indicators(df, cfg, compat=CompatSwitches.all_disabled())
    assert res.loc[0, "plhivservice_q1"] == 1
    assert res.loc[0, "definedpackage_q1"] == 1


def test_defined_package_multi_row_uic_encounter_aggregation():
    """Services distributed across multiple encounter rows of the same UIC combine to satisfy Defined Package."""
    # Row 1: HTS + STI
    # Row 2: TB + Condoms + HE_RRC
    reg_df = pd.DataFrame(
        {
            "county": ["MOMBASA", "MOMBASA"],
            "sr_name": ["SR1", "SR1"],
            "region": ["COAST", "COAST"],
            "kp_vp_unique_identifier_code": ["U999", "U999"],
            "date_of_enrolment": ["2024-01-01", "2024-01-01"],
            "hiv_tested_results_p_n_nd_na_1": ["Negative", "None"],
            "hiv_tested_results_p_n_nd_na_2": ["None", "None"],
            "hiv_tested_results_p_n_nd_na_3": ["None", "None"],
            "hiv_tested_results_p_n_nd_na_4": ["None", "None"],
            "hiv_tested_results_p_n_nd_na_5": ["None", "None"],
            "hiv_tested_results_p_n_nd_na_6": ["None", "None"],
            "screened_for_stis_y_n_1": ["Yes", "No"],
            "screened_for_stis_y_n_2": ["No", "No"],
            "screened_for_stis_y_n_3": ["No", "No"],
            "screened_for_stis_y_n_4": ["No", "No"],
            "screened_for_stis_y_n_5": ["No", "No"],
            "screened_for_stis_y_n_6": ["No", "No"],
            "screened_for_tb_1": ["No", "Yes"],
            "screened_for_tb_2": ["No", "No"],
            "screened_for_tb_3": ["No", "No"],
            "screened_for_tb_4": ["No", "No"],
            "screened_for_tb_5": ["No", "No"],
            "screened_for_tb_6": ["No", "No"],
            "condoms_distributed_indicate_number_n_a_for_inmates_1": [0, 20],
            "condoms_distributed_indicate_number_n_a_for_inmates_2": [0, 0],
            "condoms_distributed_indicate_number_n_a_for_inmates_3": [0, 0],
            "condoms_distributed_indicate_number_n_a_for_inmates_4": [0, 0],
            "condoms_distributed_indicate_number_n_a_for_inmates_5": [0, 0],
            "condoms_distributed_indicate_number_n_a_for_inmates_6": [0, 0],
            "received_peer_education_y_n_1": ["No", "Yes"],
            "received_peer_education_y_n_2": ["No", "No"],
            "received_peer_education_y_n_3": ["No", "No"],
            "received_peer_education_y_n_4": ["No", "No"],
            "received_peer_education_y_n_5": ["No", "No"],
            "received_peer_education_y_n_6": ["No", "No"],
            "provided_with_risk_reduction_counselling_y_n_1": ["No", "No"],
            "provided_with_risk_reduction_counselling_y_n_2": ["No", "No"],
            "provided_with_risk_reduction_counselling_y_n_3": ["No", "No"],
            "provided_with_risk_reduction_counselling_y_n_4": ["No", "No"],
            "provided_with_risk_reduction_counselling_y_n_5": ["No", "No"],
            "provided_with_risk_reduction_counselling_y_n_6": ["No", "No"],
        }
    )

    res = run_analytics(reg_df, population="FSW", compat=CompatSwitches.all_disabled())
    cleaned = res["cleaned_register"]
    summary = res["summary_register"]

    # In cleaned register, encounter with condoms reflects the full package
    assert cleaned.loc[1, "definedpackage_q1"] == 1

    # In modern summary, exactly 1 unique client is counted
    assert summary.loc[0, "DefinedPackage_Q1"] == 1
    assert summary.loc[0, "TotalCohort"] == 1
