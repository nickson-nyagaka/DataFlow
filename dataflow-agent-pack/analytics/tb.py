"""TB (Tuberculosis) screening indicator calculations for DATAFLOW."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.common import any_in_unique_allrows
from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_tb_indicators(df: pd.DataFrame, compat: CompatSwitches | None = None) -> pd.DataFrame:
    """Computes TB screening indicators on cleaned Register."""
    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort if compat else False
    case_insens = not compat.legacy_capitalize_vocabulary if compat else False
    q1_cols, q2_cols, _ = resolve_period_columns(
        res, r"screened_for_tb_?\d*$", required=False, lexicographic_sort=lex_sort
    )

    if q1_cols or q2_cols:
        res["tb_screened_q1"] = np.where(
            any_in_unique_allrows(res, q1_cols, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["tb_screened_q2"] = np.where(
            any_in_unique_allrows(res, q2_cols, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["tb_screened_sem"] = np.where(
            (res["tb_screened_q1"] + res["tb_screened_q2"]) >= 1, 1, 0
        )
    else:
        res["tb_screened_q1"] = 0
        res["tb_screened_q2"] = 0
        res["tb_screened_sem"] = 0

    return res
