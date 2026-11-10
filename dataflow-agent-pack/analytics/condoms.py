"""Condom distribution indicator calculations for DATAFLOW."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_condom_indicators(
    df: pd.DataFrame, compat: CompatSwitches | None = None
) -> pd.DataFrame:
    """Computes condom client-reach and total commodity distribution indicators."""
    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort if compat else False
    q1_cols, q2_cols, _ = resolve_period_columns(
        res,
        r"condoms_distributed_indicate_number_n_a_for_inmates_?\d*$",
        required=False,
        lexicographic_sort=lex_sort,
    )

    if q1_cols or q2_cols:
        # Numeric coercion
        all_cols = q1_cols + q2_cols
        res[all_cols] = res[all_cols].apply(pd.to_numeric, errors="coerce")

        res["condoms_q1"] = np.where(res[q1_cols].gt(0).any(axis=1) if q1_cols else False, 1, 0)
        res["condoms_q2"] = np.where(res[q2_cols].gt(0).any(axis=1) if q2_cols else False, 1, 0)
        res["condoms_sem"] = np.where((res["condoms_q1"] + res["condoms_q2"]) >= 1, 1, 0)

        res["total_condoms_q1"] = res[q1_cols].sum(axis=1, skipna=True) if q1_cols else 0
        res["total_condoms_q2"] = res[q2_cols].sum(axis=1, skipna=True) if q2_cols else 0
        res["total_condoms_sem"] = res["total_condoms_q1"] + res["total_condoms_q2"]
    else:
        for col in [
            "condoms_q1",
            "condoms_q2",
            "condoms_sem",
            "total_condoms_q1",
            "total_condoms_q2",
            "total_condoms_sem",
        ]:
            res[col] = 0

    return res
