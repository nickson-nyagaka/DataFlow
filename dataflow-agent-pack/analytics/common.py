"""Common helper functions for DATAFLOW analytical calculations."""

from __future__ import annotations

from typing import Any

import pandas as pd


def any_in_unique_allrows(
    df: pd.DataFrame,
    cols: list[str],
    values: list[Any],
    id_col: str = "kp_vp_unique_identifier_code",
    case_insensitive: bool = False,
) -> pd.Series:
    """Propagates client-level event occurrence across all rows of the same UIC.

    Replicates notebook Cell 61 helper:
    If client has matching value in ANY of the columns in ANY row, returns True for all rows of that client.
    """
    if not cols:
        return pd.Series(False, index=df.index)

    if case_insensitive:
        norm_values = [str(v).strip().lower() for v in values]
        row_has = (
            df[cols]
            .apply(lambda col: col.astype(str).str.strip().str.lower().isin(norm_values))
            .any(axis=1)
        )
    else:
        row_has = df[cols].isin(values).any(axis=1)

    if id_col in df.columns:
        return row_has.groupby(df[id_col]).transform("max")
    return row_has


def compute_indicator_aggregate(
    df: pd.DataFrame,
    flag_col: str,
    group_cols: list[str],
    id_col: str = "kp_vp_unique_identifier_code",
    legacy_row_sum: bool = True,
) -> pd.Series:
    """Computes group-level indicator aggregate.

    If legacy_row_sum is True: computes df[flag_col].sum() (legacy notebook behavior).
    If legacy_row_sum is False: computes unique clients with flag_col == 1 (modern client-grain).
    """
    if legacy_row_sum:
        return df.groupby(group_cols)[flag_col].sum()
    else:
        # Modern: unique client grain
        # Filter rows where indicator is positive, then nunique(id_col)
        pos = df[df[flag_col] > 0]
        if pos.empty:
            return pd.Series(0, index=df.groupby(group_cols).size().index)
        counts = pos.groupby(group_cols)[id_col].nunique()
        # Reindex to full group indices ensuring all groups are represented
        return counts.reindex(df.groupby(group_cols).size().index, fill_value=0)
