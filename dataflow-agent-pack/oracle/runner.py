"""Exact bug-compatible transcription of the legacy notebook logic into callable Python functions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from janitor import clean_names


def run_oracle(file_path: str | Path, population: str = "FSW") -> dict[str, pd.DataFrame]:
    """Runs the legacy notebook pipeline directly from an Excel workbook path."""
    p = Path(file_path)
    reg_sheet = "MSM" if population.upper() == "MSM" else "Register"
    kp_sheet = "KPLHIV"

    # Ingestion per Cell 04
    reg_df = pd.read_excel(p, skiprows=2, sheet_name=reg_sheet)
    kp_df = pd.read_excel(p, skiprows=2, sheet_name=kp_sheet)

    return run_oracle_from_dfs(reg_df, kp_df, population=population)


def run_oracle_from_dfs(
    reg_df: pd.DataFrame,
    kp_df: pd.DataFrame,
    population: str = "FSW",
) -> dict[str, Any]:
    """Runs the legacy notebook pipeline from pre-loaded Register and KPLHIV frames."""
    ConsolidatedFSW = reg_df.copy()
    ConsolidatedKPLHIV = kp_df.copy()

    # Step 1: pyjanitor clean_names (Cell 04)
    ConsolidatedFSW = clean_names(ConsolidatedFSW)
    ConsolidatedKPLHIV = clean_names(ConsolidatedKPLHIV)

    # Step 2: Clean KPLHIV (Cell 14)
    # Convert all observations to sentence case
    ConsolidatedKPLHIV = ConsolidatedKPLHIV.map(
        lambda x: str(x).capitalize() if isinstance(x, str) else x
    )
    # Remove leading and trailing spaces from all string columns
    ConsolidatedKPLHIV = ConsolidatedKPLHIV.map(lambda x: x.strip() if isinstance(x, str) else x)
    # Rename column 'program_uic' to 'kp_vp_unique_identifier_code_'
    if "program_uic" in ConsolidatedKPLHIV.columns:
        ConsolidatedKPLHIV = ConsolidatedKPLHIV.rename(
            columns={"program_uic": "kp_vp_unique_identifier_code_"}
        )
    if "ccc_no_provided_by_art_centre_" in ConsolidatedKPLHIV.columns:
        ConsolidatedKPLHIV = ConsolidatedKPLHIV.rename(
            columns={"ccc_no_provided_by_art_centre_": "ccc_number_nupi_n_a_10_digit_number_"}
        )

    for col in ["region", "kp_vp_unique_identifier_code_", "sr_name", "county"]:
        if col in ConsolidatedKPLHIV.columns:
            ConsolidatedKPLHIV[col] = ConsolidatedKPLHIV[col].str.upper()

    # Step 3: Uppercase demo columns in Register (Cell 21)
    for col in [
        "region",
        "sr_name",
        "key_vulnerable_population_type",
        "county",
        "sub_county",
        "ward",
    ]:
        if col in ConsolidatedFSW.columns:
            ConsolidatedFSW[col] = ConsolidatedFSW[col].str.upper()

    # Step 4: Strip column names in Register (Cell 43)
    ConsolidatedFSW.columns = ConsolidatedFSW.columns.str.strip()

    # Step 5: Drop 's_n' from KPLHIV (Cell 45)
    if "s_n" in ConsolidatedKPLHIV.columns:
        ConsolidatedKPLHIV = ConsolidatedKPLHIV.drop(columns=["s_n"])

    # Step 6: Viral Load standardization & suppression (Cell 54)
    def standardize_viral_load(val: Any) -> Any:
        v = str(val).strip().lower()
        if re.fullmatch(r"[<>]?ldl", v):
            return "LDL"
        match = re.search(r"[\d,]+", v)
        if match:
            return int(match.group().replace(",", ""))
        return "UNKNOWN"

    ConsolidatedKPLHIV["standardized_viral_load"] = ConsolidatedKPLHIV["levels_copies_ml_"].apply(
        standardize_viral_load
    )

    def is_suppressed(val: Any) -> bool:
        if val == "LDL":
            return True
        if isinstance(val, int) and val < 200:
            return True
        return False

    ConsolidatedKPLHIV["is_suppressed"] = ConsolidatedKPLHIV["standardized_viral_load"].apply(
        is_suppressed
    )

    summary_KPLHIV = (
        ConsolidatedKPLHIV.groupby(["county", "sr_name", "region"])
        .agg(
            Total_KPLHIV=("kp_vp_unique_identifier_code_", "nunique"),
            Suppressed=("is_suppressed", "sum"),
        )
        .reset_index()
    )

    # Step 7: Age group for Register (Cell 57)
    ConsolidatedFSW["age_group"] = ConsolidatedFSW["age"].apply(
        lambda x: (
            "15-19"
            if 15 <= x <= 19
            else ("20-24" if 20 <= x <= 24 else ("25+" if x >= 25 else "Below 15"))
        )
    )

    # Step 8: Coverage indicators (Cell 61)
    def get_cols(df: pd.DataFrame, pattern: str) -> list[str]:
        return [col for col in df.columns if re.fullmatch(pattern, col)]

    def any_in_unique_allrows(
        df: pd.DataFrame,
        cols: list[str],
        values: list[Any],
        id_col: str = "kp_vp_unique_identifier_code",
    ) -> pd.Series:
        if not cols:
            return pd.Series(False, index=df.index)
        row_has = df[cols].isin(values).any(axis=1)
        has_by_id = row_has.groupby(df[id_col]).transform("max")
        return has_by_id

    # 1. PrEP indicators
    prep_cols = sorted(get_cols(ConsolidatedFSW, r"prep_status_?\d*$"))
    prep_q1_cols = prep_cols[:3]
    prep_q2_cols = prep_cols[3:6]

    ConsolidatedFSW["prep_q1"] = np.where(
        any_in_unique_allrows(
            ConsolidatedFSW, prep_q1_cols, ["Initiated", "Restart", "Switched", "Refill"]
        ),
        1,
        0,
    )
    ConsolidatedFSW["prep_refill_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, prep_q1_cols, ["Refill"]), 1, 0
    )
    ConsolidatedFSW["prep_initiate_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, prep_q1_cols, ["Initiated"]), 1, 0
    )
    ConsolidatedFSW["prep_disc_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, prep_q1_cols, ["Discontinued"]), 1, 0
    )

    ConsolidatedFSW["prep_q2"] = np.where(
        any_in_unique_allrows(
            ConsolidatedFSW, prep_q2_cols, ["Initiated", "Restart", "Switched", "Refill"]
        ),
        1,
        0,
    )
    ConsolidatedFSW["prep_refill_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, prep_q2_cols, ["Refill"]), 1, 0
    )
    ConsolidatedFSW["prep_initiate_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, prep_q2_cols, ["Initiated"]), 1, 0
    )
    ConsolidatedFSW["prep_disc_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, prep_q2_cols, ["Discontinued"]), 1, 0
    )
    ConsolidatedFSW["prep_sem"] = np.where(
        (ConsolidatedFSW["prep_q1"] + ConsolidatedFSW["prep_q2"]) >= 1, 1, 0
    )

    # 2. HIV testing indicators
    hiv_cols = sorted(get_cols(ConsolidatedFSW, r"hiv_tested_results_p_n_nd_na_?\d*$"))
    hiv_q1_cols = hiv_cols[:3]
    hiv_q2_cols = hiv_cols[3:6]

    ConsolidatedFSW["hts_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q1_cols, ["Negative", "Positive"]), 1, 0
    )
    ConsolidatedFSW["hts_Negative_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q1_cols, ["Negative"]), 1, 0
    )
    ConsolidatedFSW["hts_Positive_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q1_cols, ["Positive"]), 1, 0
    )

    ConsolidatedFSW["hts_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q2_cols, ["Negative", "Positive"]), 1, 0
    )
    ConsolidatedFSW["hts_Negative_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q2_cols, ["Negative"]), 1, 0
    )
    ConsolidatedFSW["hts_Positive_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q2_cols, ["Positive"]), 1, 0
    )

    ConsolidatedFSW["date_of_enrolment"] = pd.to_datetime(
        ConsolidatedFSW["date_of_enrolment"], errors="coerce"
    )
    enrolled_Apr_plus = ConsolidatedFSW["date_of_enrolment"].dt.month >= 7

    ConsolidatedFSW["hts_sem"] = np.where(
        ((ConsolidatedFSW["hts_q1"] > 0) & (ConsolidatedFSW["hts_q2"] > 0))
        | ((ConsolidatedFSW["hts_q2"] > 0) & enrolled_Apr_plus),
        1,
        0,
    )
    ConsolidatedFSW["hts_sem_any"] = np.where(
        (ConsolidatedFSW["hts_q1"] > 0) | (ConsolidatedFSW["hts_q2"] > 0), 1, 0
    )

    # 3. ART outcome indicators
    art_cols = sorted(get_cols(ConsolidatedFSW, r"art_outcome_?\d*$"))
    art_q1_cols = art_cols[:3]
    art_q2_cols = art_cols[3:6]
    ConsolidatedFSW["activeart"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, art_q1_cols, ["Active", "Yes"]), 1, 0
    )
    ConsolidatedFSW["activeart_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, art_q2_cols, ["Active", "Yes"]), 1, 0
    )

    # 4. STI indicators
    sti_screened_cols = sorted(get_cols(ConsolidatedFSW, r"screened_for_stis_y_n_?\d*$"))
    sti_diag_cols = sorted(get_cols(ConsolidatedFSW, r"diagnosed_with_sti_y_n_?\d*$"))
    sti_treat_cols = sorted(get_cols(ConsolidatedFSW, r"treated_for_stis_y_n_na_r_referred_?\d*$"))

    ConsolidatedFSW["sti_screened_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, sti_screened_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["sti_screened_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, sti_screened_cols[3:6], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["sti_screened_sem"] = np.where(
        (ConsolidatedFSW["sti_screened_q1"] + ConsolidatedFSW["sti_screened_q2"]) >= 1, 1, 0
    )

    ConsolidatedFSW["sti_diagnosed_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, sti_diag_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["sti_diagnosed_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, sti_diag_cols[3:6], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["sti_diagnosed_sem"] = np.where(
        (ConsolidatedFSW["sti_diagnosed_q1"] + ConsolidatedFSW["sti_diagnosed_q2"]) >= 1, 1, 0
    )

    ConsolidatedFSW["sti_treated_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, sti_treat_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["sti_treated_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, sti_treat_cols[3:6], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["sti_treated_sem"] = np.where(
        (ConsolidatedFSW["sti_treated_q1"] + ConsolidatedFSW["sti_treated_q2"]) >= 1, 1, 0
    )

    # 5. Peer Education & RRC
    peer_ed_cols = sorted(get_cols(ConsolidatedFSW, r"received_peer_education_y_n_?\d*$"))
    rrc_cols = sorted(
        get_cols(ConsolidatedFSW, r"provided_with_risk_reduction_counselling_y_n_?\d*$")
    )

    ConsolidatedFSW["peereducation_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, peer_ed_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["peereducation_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, peer_ed_cols[3:6], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["peereducation_sem"] = np.where(
        (ConsolidatedFSW["peereducation_q1"] + ConsolidatedFSW["peereducation_q2"]) >= 1, 1, 0
    )

    ConsolidatedFSW["rrc_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, rrc_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["rrc_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, rrc_cols[3:6], ["Yes"]), 1, 0
    )

    ConsolidatedFSW["he_rrc_q1"] = np.where(
        (ConsolidatedFSW["peereducation_q1"] == 1) | (ConsolidatedFSW["rrc_q1"] == 1), 1, 0
    )
    ConsolidatedFSW["he_rrc_q2"] = np.where(
        (ConsolidatedFSW["peereducation_q2"] == 1) | (ConsolidatedFSW["rrc_q2"] == 1), 1, 0
    )

    # 6. TB screening
    tb_screened_cols = sorted(get_cols(ConsolidatedFSW, r"screened_for_tb_?\d*$"))
    ConsolidatedFSW["tb_screened_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, tb_screened_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["tb_screened_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, tb_screened_cols[3:6], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["tb_screened_sem"] = np.where(
        (ConsolidatedFSW["tb_screened_q1"] + ConsolidatedFSW["tb_screened_q2"]) >= 1, 1, 0
    )

    # 7. Condoms & NSP
    condoms_cols = sorted(
        get_cols(ConsolidatedFSW, r"condoms_distributed_indicate_number_n_a_for_inmates_?\d*$")
    )
    nsp_cols = sorted(
        get_cols(
            ConsolidatedFSW,
            r"needles_and_syringes_distributed_indicate_number_n_a_for_inmates_?\d*$",
        )
    )

    if condoms_cols or nsp_cols:
        ConsolidatedFSW[condoms_cols + nsp_cols] = ConsolidatedFSW[condoms_cols + nsp_cols].apply(
            pd.to_numeric, errors="coerce"
        )

    condoms_q1 = condoms_cols[:3]
    condoms_q2 = condoms_cols[3:6]
    nsp_q1 = nsp_cols[:3]
    nsp_q2 = nsp_cols[3:6]

    ConsolidatedFSW["condoms_q1"] = np.where(
        ConsolidatedFSW[condoms_q1].gt(0).any(axis=1) if condoms_q1 else False, 1, 0
    )
    ConsolidatedFSW["condoms_q2"] = np.where(
        ConsolidatedFSW[condoms_q2].gt(0).any(axis=1) if condoms_q2 else False, 1, 0
    )
    ConsolidatedFSW["condoms_sem"] = np.where(
        (ConsolidatedFSW["condoms_q1"] + ConsolidatedFSW["condoms_q2"]) >= 1, 1, 0
    )

    ConsolidatedFSW["total_condoms_q1"] = (
        ConsolidatedFSW[condoms_q1].sum(axis=1, skipna=True) if condoms_q1 else 0
    )
    ConsolidatedFSW["total_condoms_q2"] = (
        ConsolidatedFSW[condoms_q2].sum(axis=1, skipna=True) if condoms_q2 else 0
    )
    ConsolidatedFSW["total_condoms_sem"] = (
        ConsolidatedFSW["total_condoms_q1"] + ConsolidatedFSW["total_condoms_q2"]
    )

    ConsolidatedFSW["nsp_q1"] = np.where(
        ConsolidatedFSW[nsp_q1].gt(0).any(axis=1) if nsp_q1 else False, 1, 0
    )
    ConsolidatedFSW["nsp_q2"] = np.where(
        ConsolidatedFSW[nsp_q2].gt(0).any(axis=1) if nsp_q2 else False, 1, 0
    )
    ConsolidatedFSW["nsp_sem"] = np.where(
        (ConsolidatedFSW["nsp_q1"] + ConsolidatedFSW["nsp_q2"]) >= 1, 1, 0
    )

    ConsolidatedFSW["total_nsp_q1"] = (
        ConsolidatedFSW[nsp_q1].sum(axis=1, skipna=True) if nsp_q1 else 0
    )
    ConsolidatedFSW["total_nsp_q2"] = (
        ConsolidatedFSW[nsp_q2].sum(axis=1, skipna=True) if nsp_q2 else 0
    )

    # 8. ART / Positive / PLHIV
    onart_cols = sorted(get_cols(ConsolidatedFSW, r"currently_on_art_y_n_n_a_?\d*$"))
    ConsolidatedFSW["onart_q1"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, onart_cols[:3], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["onart_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, onart_cols[3:6], ["Yes"]), 1, 0
    )
    ConsolidatedFSW["onart_sem"] = np.where(
        (ConsolidatedFSW["onart_q1"] + ConsolidatedFSW["onart_q2"]) >= 1, 1, 0
    )

    ConsolidatedFSW["Positive_art"] = np.where(
        (ConsolidatedFSW["hts_Positive_q1"] == 1) & (ConsolidatedFSW["onart_q1"] == 1), 1, 0
    )
    ConsolidatedFSW["Positive_art_q2"] = np.where(
        (ConsolidatedFSW["hts_Positive_q2"] == 1) & (ConsolidatedFSW["onart_q2"] == 1), 1, 0
    )

    ConsolidatedFSW["plhiv"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q1_cols, ["Known positive"]), 1, 0
    )
    ConsolidatedFSW["plhiv_q2"] = np.where(
        any_in_unique_allrows(ConsolidatedFSW, hiv_q2_cols, ["Known positive"]), 1, 0
    )

    # 9. PLHIV Service (NSP commented out per notebook Cell 61)
    ConsolidatedFSW["plhivservice_q1"] = np.where(
        (ConsolidatedFSW["plhiv"] == 1)
        & (ConsolidatedFSW["sti_screened_q1"] == 1)
        & (ConsolidatedFSW["condoms_q1"] == 1)
        & (ConsolidatedFSW["he_rrc_q1"] == 1)
        & (ConsolidatedFSW["tb_screened_q1"] == 1),
        1,
        0,
    )
    ConsolidatedFSW["plhivservice_q2"] = np.where(
        (ConsolidatedFSW["plhiv_q2"] == 1)
        & (ConsolidatedFSW["sti_screened_q2"] == 1)
        & (ConsolidatedFSW["condoms_q2"] == 1)
        & (ConsolidatedFSW["he_rrc_q2"] == 1)
        & (ConsolidatedFSW["tb_screened_q2"] == 1),
        1,
        0,
    )

    # 10. Defined Package (NSP commented out per notebook Cell 61)
    ConsolidatedFSW["definedpackage_q1"] = np.where(
        (
            (ConsolidatedFSW["hts_q1"] == 1)
            & (ConsolidatedFSW["sti_screened_q1"] == 1)
            & (ConsolidatedFSW["tb_screened_q1"] == 1)
            & (ConsolidatedFSW["condoms_q1"] == 1)
            & (ConsolidatedFSW["he_rrc_q1"] == 1)
        )
        | (ConsolidatedFSW["plhivservice_q1"] == 1),
        1,
        0,
    )
    ConsolidatedFSW["definedpackage_q2"] = np.where(
        (
            (ConsolidatedFSW["hts_q2"] == 1)
            & (ConsolidatedFSW["sti_screened_q2"] == 1)
            & (ConsolidatedFSW["tb_screened_q2"] == 1)
            & (ConsolidatedFSW["condoms_q2"] == 1)
            & (ConsolidatedFSW["he_rrc_q2"] == 1)
        )
        | (ConsolidatedFSW["plhivservice_q2"] == 1),
        1,
        0,
    )
    ConsolidatedFSW["definedpackage_sem"] = np.where(
        (ConsolidatedFSW["definedpackage_q1"] + ConsolidatedFSW["definedpackage_q2"]) >= 1, 1, 0
    )

    # Step 9: Summary Aggregations (Cell 66 & Exporters)
    age_group_counts = (
        ConsolidatedFSW.groupby(["county", "sr_name", "region", "age_group"])
        .size()
        .reset_index(name="total")
        .pivot_table(
            index=["county", "sr_name", "region"],
            columns="age_group",
            values="total",
            fill_value=0,
        )
        .reset_index()
    )

    # Aggregation definitions
    summary_FSW = (
        ConsolidatedFSW.groupby(["county", "sr_name", "region"])
        .agg(
            TotalCohort=("kp_vp_unique_identifier_code", "nunique"),
            TotalPE=("peer_educator_code", "nunique"),
            HTSQ1=("hts_q1", "sum"),
            HTSQ2=("hts_q2", "sum"),
            HTS_SEM=("hts_sem", "sum"),
            HTS_SEM_ANY=("hts_sem_any", "sum"),
            HTS_Negative=("hts_Negative_q1", "sum"),
            HTS_Negative_Q2=("hts_Negative_q2", "sum"),
            HTS_Positive=("hts_Positive_q1", "sum"),
            HTS_Positive_Q2=("hts_Positive_q2", "sum"),
            DefinedPackage_Q1=("definedpackage_q1", "sum"),
            DefinedPackage_Q2=("definedpackage_q2", "sum"),
            DefinedPackage_SEM=("definedpackage_sem", "sum"),
            New_on_ART=("Positive_art", "sum"),
            New_on_ART_Q2=("Positive_art_q2", "sum"),
            PLHIV_Q1=("plhiv", "sum"),
            PLHIV_Q2=("plhiv_q2", "sum"),
            CurrentArt_Q1=("onart_q1", "sum"),
            CurrentArt_Q2=("onart_q2", "sum"),
            ReceivedCondom_Q1=("condoms_q1", "sum"),
            ReceivedCondom_Q2=("condoms_q2", "sum"),
            ReceivedCondom_SEM=("condoms_sem", "sum"),
            STISCREENEDQ_1=("sti_screened_q1", "sum"),
            STISCREENEDQ_2=("sti_screened_q2", "sum"),
            STI_SCREENED_SEM=("sti_screened_sem", "sum"),
            STIDiagnosid_Q1=("sti_diagnosed_q1", "sum"),
            STI_DIAGNOSED_Q2=("sti_diagnosed_q2", "sum"),
            STI_DIAGNOSED_SEM=("sti_diagnosed_sem", "sum"),
            STItreated_Q1=("sti_treated_q1", "sum"),
            STI_TREATED_Q2=("sti_treated_q2", "sum"),
            STI_TREATED_SEM=("sti_treated_sem", "sum"),
            TB_SCREENED_Q1=("tb_screened_q1", "sum"),
            TB_SCREENED_Q2=("tb_screened_q2", "sum"),
            TB_SCREENED_SEM=("tb_screened_sem", "sum"),
            PeerEducation_Q1=("peereducation_q1", "sum"),
            PeerEducation_Q2=("peereducation_q2", "sum"),
            PeerEducation_SEM=("peereducation_sem", "sum"),
            HE_RRC_Q1=("he_rrc_q1", "sum"),
            HE_RRC_Q2=("he_rrc_q2", "sum"),
            PREP_Q1=("prep_q1", "sum"),
            PREP_Q2=("prep_q2", "sum"),
            PREP_SEM=("prep_sem", "sum"),
            NSP_Q1=("nsp_q1", "sum"),
            NSP_Q2=("nsp_q2", "sum"),
            NSP_SEM=("nsp_sem", "sum"),
            total_condoms_Q1=("total_condoms_q1", "sum"),
            total_condoms_Q2=("total_condoms_q2", "sum"),
            total_condoms_SEM=("total_condoms_sem", "sum"),
            total_nsp_Q1=("total_nsp_q1", "sum"),
            total_nsp_Q2=("total_nsp_q2", "sum"),
        )
        .reset_index()
    )

    # Standardize join keys with title-case (Cell 67)
    for df in [summary_FSW, summary_KPLHIV, age_group_counts]:
        for col in ["county", "sr_name", "region"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()

    # Merge into final_summary_FSW (Cell 69)
    final_df = pd.merge(summary_FSW, summary_KPLHIV, on=["county", "sr_name", "region"], how="left")
    final_df = pd.merge(final_df, age_group_counts, on=["county", "sr_name", "region"], how="left")

    return {
        "final_summary": final_df,
        "summary_fsw": summary_FSW,
        "summary_kplhiv": summary_KPLHIV,
        "age_group_counts": age_group_counts,
        "cleaned_register": ConsolidatedFSW,
        "cleaned_kplhiv": ConsolidatedKPLHIV,
    }
