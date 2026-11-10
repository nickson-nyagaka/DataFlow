"""Deduplication detection and analysis for DATAFLOW.

Strictly adheres to:
- AGENTS.md §5.2: Never auto-delete duplicate UICs; never silently drop or merge records.
- D-004 & D-017 (OQ-04): Flag all rows sharing a duplicate UIC (keep=False) so M&E officers
  can review duplicate encounter rows side-by-side. Analytical indicators aggregate at
  client grain (nunique UIC).
"""

from __future__ import annotations

import pandas as pd


def identify_duplicate_uics(
    df: pd.DataFrame,
    uic_col: str = "kp_vp_unique_identifier_code",
) -> pd.DataFrame:
    """Identifies all duplicate UIC encounters without removing or mutating any records.

    Returns:
        DataFrame containing all rows that share a duplicated UIC (keep=False),
        sorted by UIC so duplicates can be reviewed side-by-side.
        Empty DataFrame if no duplicates exist.
    """
    if uic_col not in df.columns:
        return pd.DataFrame(columns=df.columns)

    # Filter out null / empty UICs first (null UICs are handled by missing UIC rule)
    valid_uics = df[uic_col].dropna()
    valid_uics = valid_uics[valid_uics.astype(str).str.strip() != ""]

    duplicate_mask = df[uic_col].isin(valid_uics[valid_uics.duplicated(keep=False)])

    if not duplicate_mask.any():
        return pd.DataFrame(columns=df.columns)

    dups = df[duplicate_mask].copy()
    dups["_duplicate_count"] = dups.groupby(uic_col)[uic_col].transform("count")
    dups = dups.sort_values(by=[uic_col]).reset_index(drop=False)
    dups = dups.rename(columns={"index": "_original_row_index"})
    return dups


def get_duplicate_uic_summary(
    df: pd.DataFrame,
    uic_col: str = "kp_vp_unique_identifier_code",
) -> dict[str, int]:
    """Computes summary statistics on duplicate UICs."""
    if uic_col not in df.columns:
        return {"total_rows": len(df), "unique_uics": 0, "duplicate_uics": 0, "duplicate_rows": 0}

    valid_uics = df[uic_col].dropna()
    valid_uics = valid_uics[valid_uics.astype(str).str.strip() != ""]

    uic_counts = valid_uics.value_counts()
    dup_uics = uic_counts[uic_counts > 1]

    return {
        "total_rows": len(df),
        "unique_uics": int(valid_uics.nunique()),
        "duplicate_uics": int(len(dup_uics)),
        "duplicate_rows": int(dup_uics.sum()),
    }
