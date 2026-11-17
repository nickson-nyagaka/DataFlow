"""PrEP (Pre-Exposure Prophylaxis) indicator calculations for DATAFLOW."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.common import any_in_unique_allrows
from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_prep_indicators(df: pd.DataFrame, compat: CompatSwitches | None = None) -> pd.DataFrame:
    """Computes PrEP indicators on a cleaned Register DataFrame.

    Indicators:
    - prep_q1, prep_refill_q1, prep_initiate_q1, prep_switched_q1, prep_disc_q1
    - prep_q2, prep_refill_q2, prep_initiate_q2, prep_switched_q2, prep_disc_q2
    - prep_sem
    """
    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort if compat else False
    case_insens = not compat.legacy_capitalize_vocabulary if compat else False
    q1_cols, q2_cols, _ = resolve_period_columns(
        res, r"prep_status_?\d*$", required=False, lexicographic_sort=lex_sort
    )

    if not q1_cols and not q2_cols:
        for col in [
            "prep_q1",
            "prep_refill_q1",
            "prep_initiate_q1",
            "prep_restart_q1",
            "prep_switched_q1",
            "prep_disc_q1",
            "prep_q2",
            "prep_refill_q2",
            "prep_initiate_q2",
            "prep_restart_q2",
            "prep_switched_q2",
            "prep_disc_q2",
            "prep_sem",
        ]:
            res[col] = 0
        return res

    active_prep = [
        "Initiated", "Restart", "Restarted", "Switched", "Switch", "Refill", "Refilled",
        "initiated", "restart", "restarted", "switched", "switch", "refill", "refilled",
    ]
    refill_variants = [
        "Refill", "refill", "Refilled", "refilled",
    ]
    restart_variants = [
        "Restart", "restart", "Restarted", "restarted",
    ]
    switched_variants = [
        "Switched", "switched", "Switch", "switch",
    ]
    initiate_variants = ["Initiated", "initiated"]
    disc_variants = ["Discontinued", "discontinued"]

    # Q1: unique per peer in Q1
    res["prep_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, active_prep, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_refill_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, refill_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_initiate_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, initiate_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_restart_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, restart_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_switched_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, switched_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_disc_q1"] = np.where(
        any_in_unique_allrows(res, q1_cols, disc_variants, case_insensitive=case_insens),
        1,
        0,
    )

    # Q2: unique per peer in Q2
    res["prep_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, active_prep, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_refill_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, refill_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_initiate_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, initiate_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_restart_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, restart_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_switched_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, switched_variants, case_insensitive=case_insens),
        1,
        0,
    )
    res["prep_disc_q2"] = np.where(
        any_in_unique_allrows(res, q2_cols, disc_variants, case_insensitive=case_insens),
        1,
        0,
    )

    # SEM: summation of Q1 + Q2
    res["prep_sem"] = res["prep_q1"] + res["prep_q2"]

    return res
