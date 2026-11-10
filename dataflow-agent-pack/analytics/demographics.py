"""Demographic analytics: Age grouping and Sex disaggregations for DATAFLOW."""

from __future__ import annotations

import pandas as pd

from core.compat import CompatSwitches


def assign_age_groups(
    df: pd.DataFrame,
    age_col: str = "age",
    compat: CompatSwitches | None = None,
) -> pd.Series:
    """Assigns standard 4-tier age bands to a cleaned Register DataFrame.

    Bands:
    - 15-19
    - 20-24
    - 25+
    - Below 15
    - Unknown (modern D-021) vs Below 15 (legacy defect in notebook cell 57)
    """
    if compat is None:
        compat = CompatSwitches()

    if age_col not in df.columns:
        default_missing = "Below 15" if compat.legacy_missing_age_below_15 else "Unknown"
        return pd.Series(default_missing, index=df.index)

    ages = pd.to_numeric(df[age_col], errors="coerce")

    def classify_age(x: float) -> str:
        if pd.isna(x):
            return "Below 15" if compat.legacy_missing_age_below_15 else "Unknown"
        if 15 <= x <= 19:
            return "15-19"
        if 20 <= x <= 24:
            return "20-24"
        if x >= 25:
            return "25+"
        return "Below 15"

    return ages.apply(classify_age)


def compute_age_group_counts(
    df: pd.DataFrame,
    group_cols: list[str] | None = None,
    compat: CompatSwitches | None = None,
) -> pd.DataFrame:
    """Computes pivoted age group counts by county, sr_name, and region (notebook cell 66)."""
    if group_cols is None:
        group_cols = ["county", "sr_name", "region"]

    res = df.copy()
    if "age_group" not in res.columns:
        res["age_group"] = assign_age_groups(res, compat=compat)

    valid_group_cols = [c for c in group_cols if c in res.columns]

    counts = (
        res.groupby(valid_group_cols + ["age_group"])
        .size()
        .reset_index(name="total")
        .pivot_table(
            index=valid_group_cols,
            columns="age_group",
            values="total",
            fill_value=0,
        )
        .reset_index()
    )

    return counts
