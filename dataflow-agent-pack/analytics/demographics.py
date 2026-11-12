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


def compute_kpi_demographic_summary(
    df: pd.DataFrame,
    period_mode: str = "Q1",
    compat: CompatSwitches | None = None,
) -> pd.DataFrame:
    """Computes the 24-column KPI Indicators by Age and Sex table (notebook cell 84).

    Indicators:
    - DEFINED PACKAGE (definedpackage_q1 or definedpackage_sem)
    - HTS (hts_q1 or hts_sem_any)
    - PREP (prep_q1 or prep_sem)

    Disaggregated across 6 age x sex combinations:
    15-19_M, 15-19_F, 20-24_M, 20-24_F, 25+_M, 25+_F, and Total per indicator.
    Grouped by sr_name, region, county (uppercase).
    """
    if compat is None:
        compat = CompatSwitches()

    kvp = df.copy()

    # Ensure age numeric and assign age groups
    ages = pd.to_numeric(kvp.get("age", pd.Series(dtype=float)), errors="coerce")

    def classify_age(x: float) -> str:
        if pd.isna(x):
            return "Unknown"
        if 15 <= x <= 19:
            return "15-19"
        if 20 <= x <= 24:
            return "20-24"
        if x >= 25:
            return "25+"
        return "Below 15"

    kvp["age_group"] = ages.apply(classify_age)

    # Standardize sex values per cell 84
    sex_col = "sex_m_f_" if "sex_m_f_" in kvp.columns else "sex"
    if sex_col in kvp.columns:
        sex_clean = (
            kvp[sex_col]
            .astype(str)
            .str.strip()
            .str.upper()
            .replace({"MALE": "M", "FEMALE": "F"})
        )
        if compat and compat.legacy_impute_missing_sex_f:
            sex_clean = sex_clean.fillna("F")
    else:
        sex_clean = pd.Series(
            "F" if (compat and compat.legacy_impute_missing_sex_f) else "Unknown",
            index=kvp.index,
        )

    kvp["sex_group"] = sex_clean
    kvp["age_sex_group"] = kvp["age_group"] + "_" + kvp["sex_group"]

    # Determine indicators based on period_mode
    mode_upper = period_mode.upper()
    if mode_upper in ["Q1", "Q2"]:
        p_sfx = f"_{mode_upper.lower()}"
        def_pkg_col = f"definedpackage{p_sfx}"
        hts_col = f"hts{p_sfx}"
        prep_col = f"prep{p_sfx}"
    else:
        def_pkg_col = "definedpackage_sem"
        hts_col = "hts_sem_any" if "hts_sem_any" in kvp.columns else "hts_sem"
        prep_col = "prep_sem"

    indicator_map = {
        def_pkg_col: "DEFINED PACKAGE",
        hts_col: "HTS",
        prep_col: "PREP",
    }

    group_cols = ["sr_name", "region", "county"]
    for col in group_cols:
        if col in kvp.columns:
            kvp[col] = kvp[col].astype(str).str.strip().str.upper()
        else:
            kvp[col] = "(MISSING)"

    age_sex_order = [
        "15-19_M",
        "15-19_F",
        "20-24_M",
        "20-24_F",
        "25+_M",
        "25+_F",
    ]

    block_tables = []
    for ind_col, block_name in indicator_map.items():
        if ind_col not in kvp.columns:
            kvp[ind_col] = 0

        block = kvp.pivot_table(
            index=group_cols,
            columns="age_sex_group",
            values=ind_col,
            aggfunc="sum",
            fill_value=0,
        )
        block = block.reindex(columns=age_sex_order, fill_value=0)
        block.columns = [f"{block_name}_{ag}" for ag in block.columns]
        block[f"{block_name}_Total"] = block.sum(axis=1)
        block_tables.append(block)

    kpi_summary = pd.concat(block_tables, axis=1).reset_index()
    return kpi_summary
