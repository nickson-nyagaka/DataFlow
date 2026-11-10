"""HTS (HIV Testing Services) indicator calculations for DATAFLOW."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.common import any_in_unique_allrows
from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_hts_indicators(
    df: pd.DataFrame,
    compat: CompatSwitches | None = None,
) -> pd.DataFrame:
    """Computes HTS testing and outcome indicators on a cleaned Register DataFrame.

    Indicators:
    - hts_q1, hts_Negative_q1, hts_Positive_q1
    - hts_q2, hts_Negative_q2, hts_Positive_q2
    - hts_sem_any
    - hts_sem (controlled by compat.legacy_hts_sem_month_ge_7 per D-024)
    """
    if compat is None:
        compat = CompatSwitches()

    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort
    case_insens = not compat.legacy_capitalize_vocabulary
    q1_cols, q2_cols, _ = resolve_period_columns(
        res,
        r"hiv_tested_results_p_n_nd_na_?\d*$",
        required=False,
        lexicographic_sort=lex_sort,
    )

    if not q1_cols and not q2_cols:
        for col in [
            "hts_q1",
            "hts_Negative_q1",
            "hts_Positive_q1",
            "hts_q2",
            "hts_Negative_q2",
            "hts_Positive_q2",
            "hts_sem",
            "hts_sem_any",
        ]:
            res[col] = 0
        return res

    # Q1
    res["hts_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, ["Negative", "Positive"], case_insensitive=case_insens),
        1,
        0,
    )
    res["hts_Negative_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, ["Negative"], case_insensitive=case_insens),
        1,
        0,
    )
    res["hts_Positive_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, ["Positive"], case_insensitive=case_insens),
        1,
        0,
    )

    # Q2
    res["hts_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, ["Negative", "Positive"], case_insensitive=case_insens),
        1,
        0,
    )
    res["hts_Negative_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, ["Negative"], case_insensitive=case_insens),
        1,
        0,
    )
    res["hts_Positive_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, ["Positive"], case_insensitive=case_insens),
        1,
        0,
    )

    # SEM ANY
    res["hts_sem_any"] = np.where((res["hts_q1"] > 0) | (res["hts_q2"] > 0), 1, 0)

    # SEM
    if compat.legacy_hts_sem_month_ge_7:
        # Legacy notebook Cell 61: tested in Q1 and Q2, or tested in Q2 and enrolled in July+ (month >= 7)
        if "date_of_enrolment" in res.columns:
            enrol_dt = pd.to_datetime(res["date_of_enrolment"], errors="coerce")
            enrolled_Apr_plus = enrol_dt.dt.month >= 7
        else:
            enrolled_Apr_plus = pd.Series(False, index=res.index)
        res["hts_sem"] = np.where(
            ((res["hts_q1"] > 0) & (res["hts_q2"] > 0)) | ((res["hts_q2"] > 0) & enrolled_Apr_plus),
            1,
            0,
        )
    else:
        # Modern D-024 (OQ-06): any test in semester
        res["hts_sem"] = np.where((res["hts_q1"] > 0) | (res["hts_q2"] > 0), 1, 0)

    return res
