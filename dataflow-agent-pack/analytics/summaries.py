"""Summary aggregation engine merging Register indicators, KPLHIV metrics, and Demographics."""

from __future__ import annotations

import pandas as pd

from analytics.common import compute_indicator_aggregate
from core.compat import CompatSwitches


def build_register_summary(
    df: pd.DataFrame,
    compat: CompatSwitches | None = None,
) -> pd.DataFrame:
    """Aggregates all 48 indicator columns by county, sr_name, and region (notebook cell 66)."""
    if compat is None:
        compat = CompatSwitches()

    group_cols = [c for c in ["county", "sr_name", "region"] if c in df.columns]
    if not group_cols:
        group_cols = ["county"]
        if "county" not in df.columns:
            df = df.copy()
            df["county"] = "Unknown"
    legacy_row_sum = compat.legacy_row_sum_flags

    # TotalCohort & TotalPE
    total_cohort = df.groupby(group_cols)["kp_vp_unique_identifier_code"].nunique()
    total_pe = (
        df.groupby(group_cols)["peer_educator_code"].nunique()
        if "peer_educator_code" in df.columns
        else 0
    )

    agg_data = {
        "TotalCohort": total_cohort,
        "TotalPE": total_pe,
        "HTSQ1": compute_indicator_aggregate(
            df, "hts_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTSQ2": compute_indicator_aggregate(
            df, "hts_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTS_SEM": compute_indicator_aggregate(
            df, "hts_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTS_SEM_ANY": compute_indicator_aggregate(
            df, "hts_sem_any", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTS_Negative": compute_indicator_aggregate(
            df, "hts_Negative_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTS_Negative_Q2": compute_indicator_aggregate(
            df, "hts_Negative_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTS_Positive": compute_indicator_aggregate(
            df, "hts_Positive_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HTS_Positive_Q2": compute_indicator_aggregate(
            df, "hts_Positive_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "DefinedPackage_Q1": compute_indicator_aggregate(
            df, "definedpackage_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "DefinedPackage_Q2": compute_indicator_aggregate(
            df, "definedpackage_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "DefinedPackage_SEM": compute_indicator_aggregate(
            df, "definedpackage_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "New_on_ART": compute_indicator_aggregate(
            df, "Positive_art", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "New_on_ART_Q2": compute_indicator_aggregate(
            df, "Positive_art_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PLHIV_Q1": compute_indicator_aggregate(
            df, "plhiv", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PLHIV_Q2": compute_indicator_aggregate(
            df, "plhiv_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "CurrentArt_Q1": compute_indicator_aggregate(
            df, "onart_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "CurrentArt_Q2": compute_indicator_aggregate(
            df, "onart_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "ReceivedCondom_Q1": compute_indicator_aggregate(
            df, "condoms_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "ReceivedCondom_Q2": compute_indicator_aggregate(
            df, "condoms_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "ReceivedCondom_SEM": compute_indicator_aggregate(
            df, "condoms_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STISCREENEDQ_1": compute_indicator_aggregate(
            df, "sti_screened_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STISCREENEDQ_2": compute_indicator_aggregate(
            df, "sti_screened_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STI_SCREENED_SEM": compute_indicator_aggregate(
            df, "sti_screened_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STIDiagnosid_Q1": compute_indicator_aggregate(
            df, "sti_diagnosed_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STI_DIAGNOSED_Q2": compute_indicator_aggregate(
            df, "sti_diagnosed_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STI_DIAGNOSED_SEM": compute_indicator_aggregate(
            df, "sti_diagnosed_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STItreated_Q1": compute_indicator_aggregate(
            df, "sti_treated_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STI_TREATED_Q2": compute_indicator_aggregate(
            df, "sti_treated_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "STI_TREATED_SEM": compute_indicator_aggregate(
            df, "sti_treated_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "TB_SCREENED_Q1": compute_indicator_aggregate(
            df, "tb_screened_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "TB_SCREENED_Q2": compute_indicator_aggregate(
            df, "tb_screened_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "TB_SCREENED_SEM": compute_indicator_aggregate(
            df, "tb_screened_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PeerEducation_Q1": compute_indicator_aggregate(
            df, "peereducation_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PeerEducation_Q2": compute_indicator_aggregate(
            df, "peereducation_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PeerEducation_SEM": compute_indicator_aggregate(
            df, "peereducation_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HE_RRC_Q1": compute_indicator_aggregate(
            df, "he_rrc_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "HE_RRC_Q2": compute_indicator_aggregate(
            df, "he_rrc_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PREP_Q1": compute_indicator_aggregate(
            df, "prep_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PREP_Q2": compute_indicator_aggregate(
            df, "prep_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "PREP_SEM": compute_indicator_aggregate(
            df, "prep_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "NSP_Q1": compute_indicator_aggregate(
            df, "nsp_q1", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "NSP_Q2": compute_indicator_aggregate(
            df, "nsp_q2", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "NSP_SEM": compute_indicator_aggregate(
            df, "nsp_sem", group_cols, legacy_row_sum=legacy_row_sum
        ),
        "total_condoms_Q1": df.groupby(group_cols)["total_condoms_q1"].sum()
        if "total_condoms_q1" in df.columns
        else 0,
        "total_condoms_Q2": df.groupby(group_cols)["total_condoms_q2"].sum()
        if "total_condoms_q2" in df.columns
        else 0,
        "total_condoms_SEM": df.groupby(group_cols)["total_condoms_sem"].sum()
        if "total_condoms_sem" in df.columns
        else 0,
        "total_nsp_Q1": df.groupby(group_cols)["total_nsp_q1"].sum()
        if "total_nsp_q1" in df.columns
        else 0,
        "total_nsp_Q2": df.groupby(group_cols)["total_nsp_q2"].sum()
        if "total_nsp_q2" in df.columns
        else 0,
    }

    summary_df = pd.DataFrame(agg_data).reset_index()
    return summary_df


def merge_final_summary(
    summary_register: pd.DataFrame,
    summary_kplhiv: pd.DataFrame,
    age_group_counts: pd.DataFrame,
) -> pd.DataFrame:
    """Standardizes keys with title-case and merges summaries into final summary frame (notebook cells 67, 69)."""
    keys = ["county", "sr_name", "region"]

    # Title-case keys per cell 67
    s_reg = summary_register.copy()
    s_kp = summary_kplhiv.copy()
    s_age = age_group_counts.copy()

    for d in [s_reg, s_kp, s_age]:
        for k in keys:
            if k in d.columns:
                d[k] = d[k].astype(str).str.strip().str.title()

    kp_keys = [k for k in keys if k in s_reg.columns and k in s_kp.columns]
    age_keys = [k for k in keys if k in s_reg.columns and k in s_age.columns]

    final_df = pd.merge(s_reg, s_kp, on=kp_keys, how="left") if kp_keys else s_reg
    final_df = pd.merge(final_df, s_age, on=age_keys, how="left") if age_keys else final_df
    return final_df
