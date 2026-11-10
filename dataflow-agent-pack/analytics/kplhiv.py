"""KPLHIV (Key Population Living with HIV) analytics and summary aggregation."""

from __future__ import annotations

import pandas as pd

from analytics.viral_load import is_viral_load_suppressed, parse_and_standardize_viral_load
from core.compat import CompatSwitches


def process_kplhiv_frame(
    kplhiv_df: pd.DataFrame,
    compat: CompatSwitches | None = None,
) -> pd.DataFrame:
    """Processes cleaned KPLHIV sheet DataFrame, standardizing viral loads and suppression flags."""
    res = kplhiv_df.copy()

    # Find viral load column
    vl_col = None
    for col in ["levels_copies_ml_", "levels_copies_ml", "viral_load", "vl_results"]:
        if col in res.columns:
            vl_col = col
            break

    if vl_col:
        res["standardized_viral_load"] = res[vl_col].apply(
            lambda x: parse_and_standardize_viral_load(x, compat=compat)
        )
        res["is_suppressed"] = res["standardized_viral_load"].apply(is_viral_load_suppressed)
    else:
        res["standardized_viral_load"] = "UNKNOWN"
        res["is_suppressed"] = False

    return res


def compute_kplhiv_summary(
    processed_kplhiv_df: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregates KPLHIV summary metrics by county, sr_name, and region (notebook cell 54)."""
    if processed_kplhiv_df.empty:
        return pd.DataFrame(columns=["county", "sr_name", "region", "Total_KPLHIV", "Suppressed"])

    # Determine UIC column
    uic_col = "kp_vp_unique_identifier_code"
    for col in ["kp_vp_unique_identifier_code_", "program_uic", "kp_vp_unique_identifier_code"]:
        if col in processed_kplhiv_df.columns:
            uic_col = col
            break

    # Grouping columns
    group_cols = [c for c in ["county", "sr_name", "region"] if c in processed_kplhiv_df.columns]
    if not group_cols:
        return pd.DataFrame(columns=["county", "sr_name", "region", "Total_KPLHIV", "Suppressed"])

    summary = (
        processed_kplhiv_df.groupby(group_cols)
        .agg(
            Total_KPLHIV=(uic_col, "nunique"),
            Suppressed=("is_suppressed", "sum"),
        )
        .reset_index()
    )

    return summary
