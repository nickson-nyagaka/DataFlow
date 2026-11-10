"""STI (Sexually Transmitted Infections) indicator calculations for DATAFLOW."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.common import any_in_unique_allrows
from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_sti_indicators(df: pd.DataFrame, compat: CompatSwitches | None = None) -> pd.DataFrame:
    """Computes STI screening, diagnosis, and treatment indicators on cleaned Register."""
    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort if compat else False
    case_insens = not compat.legacy_capitalize_vocabulary if compat else False

    # Screened
    s_q1, s_q2, _ = resolve_period_columns(
        res, r"screened_for_stis_y_n_?\d*$", required=False, lexicographic_sort=lex_sort
    )
    if s_q1 or s_q2:
        res["sti_screened_q1"] = np.where(
            any_in_unique_allrows(res, s_q1, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["sti_screened_q2"] = np.where(
            any_in_unique_allrows(res, s_q2, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["sti_screened_sem"] = np.where(
            (res["sti_screened_q1"] + res["sti_screened_q2"]) >= 1, 1, 0
        )
    else:
        res["sti_screened_q1"] = 0
        res["sti_screened_q2"] = 0
        res["sti_screened_sem"] = 0

    # Diagnosed
    d_q1, d_q2, _ = resolve_period_columns(
        res, r"diagnosed_with_sti_y_n_?\d*$", required=False, lexicographic_sort=lex_sort
    )
    if d_q1 or d_q2:
        res["sti_diagnosed_q1"] = np.where(
            any_in_unique_allrows(res, d_q1, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["sti_diagnosed_q2"] = np.where(
            any_in_unique_allrows(res, d_q2, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["sti_diagnosed_sem"] = np.where(
            (res["sti_diagnosed_q1"] + res["sti_diagnosed_q2"]) >= 1, 1, 0
        )
    else:
        res["sti_diagnosed_q1"] = 0
        res["sti_diagnosed_q2"] = 0
        res["sti_diagnosed_sem"] = 0

    # Treated
    t_q1, t_q2, _ = resolve_period_columns(
        res,
        r"treated_for_stis_y_n_na_r_referred_?\d*$",
        required=False,
        lexicographic_sort=lex_sort,
    )
    if t_q1 or t_q2:
        res["sti_treated_q1"] = np.where(
            any_in_unique_allrows(res, t_q1, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["sti_treated_q2"] = np.where(
            any_in_unique_allrows(res, t_q2, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["sti_treated_sem"] = np.where(
            (res["sti_treated_q1"] + res["sti_treated_q2"]) >= 1, 1, 0
        )
    else:
        res["sti_treated_q1"] = 0
        res["sti_treated_q2"] = 0
        res["sti_treated_sem"] = 0

    return res
