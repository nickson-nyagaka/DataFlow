"""ART (Antiretroviral Therapy) and PLHIV indicator calculations for DATAFLOW."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.common import any_in_unique_allrows
from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_art_indicators(df: pd.DataFrame, compat: CompatSwitches | None = None) -> pd.DataFrame:
    """Computes ART and PLHIV indicators on a cleaned Register DataFrame.

    Indicators:
    - activeart, activeart_q2
    - onart_q1, onart_q2, onart_sem
    - Positive_art, Positive_art_q2 (New on ART)
    - plhiv, plhiv_q2
    """
    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort if compat else False
    case_insens = not compat.legacy_capitalize_vocabulary if compat else False

    # Active ART outcomes
    art_q1_cols, art_q2_cols, _ = resolve_period_columns(
        res, r"art_outcome_?\d*$", required=False, lexicographic_sort=lex_sort
    )
    if art_q1_cols or art_q2_cols:
        res["activeart"] = np.where(
            any_in_unique_allrows(
                res, art_q1_cols, ["Active", "Yes"], case_insensitive=case_insens
            ),
            1,
            0,
        )
        res["activeart_q2"] = np.where(
            any_in_unique_allrows(
                res, art_q2_cols, ["Active", "Yes"], case_insensitive=case_insens
            ),
            1,
            0,
        )
    else:
        res["activeart"] = 0
        res["activeart_q2"] = 0

    # Currently on ART
    onart_q1_cols, onart_q2_cols, _ = resolve_period_columns(
        res, r"currently_on_art_y_n_n_a_?\d*$", required=False, lexicographic_sort=lex_sort
    )
    if onart_q1_cols or onart_q2_cols:
        res["onart_q1"] = np.where(
            any_in_unique_allrows(res, onart_q1_cols, ["Yes"], case_insensitive=case_insens),
            1,
            0,
        )
        res["onart_q2"] = np.where(
            any_in_unique_allrows(res, onart_q2_cols, ["Yes"], case_insensitive=case_insens),
            1,
            0,
        )
        res["onart_sem"] = np.where((res["onart_q1"] + res["onart_q2"]) >= 1, 1, 0)
    else:
        res["onart_q1"] = 0
        res["onart_q2"] = 0
        res["onart_sem"] = 0

    # New on ART (Positive in quarter AND on ART in quarter)
    hts_pos_q1 = res["hts_Positive_q1"] if "hts_Positive_q1" in res.columns else 0
    hts_pos_q2 = res["hts_Positive_q2"] if "hts_Positive_q2" in res.columns else 0

    res["Positive_art"] = np.where((hts_pos_q1 == 1) & (res["onart_q1"] == 1), 1, 0)
    res["Positive_art_q2"] = np.where((hts_pos_q2 == 1) & (res["onart_q2"] == 1), 1, 0)

    # Known Positive (PLHIV) in quarter
    hiv_q1_cols, hiv_q2_cols, _ = resolve_period_columns(
        res, r"hiv_tested_results_p_n_nd_na_?\d*$", required=False, lexicographic_sort=lex_sort
    )
    if compat and compat.legacy_capitalize_vocabulary:
        known_pos_variants = ["Known positive"]
    else:
        known_pos_variants = [
            "Known positive",
            "Known Positive",
            "known positive",
            "KNOWN POSITIVE",
        ]

    if hiv_q1_cols or hiv_q2_cols:
        res["plhiv"] = np.where(
            any_in_unique_allrows(
                res, hiv_q1_cols, known_pos_variants, case_insensitive=case_insens
            ),
            1,
            0,
        )
        res["plhiv_q2"] = np.where(
            any_in_unique_allrows(
                res, hiv_q2_cols, known_pos_variants, case_insensitive=case_insens
            ),
            1,
            0,
        )
    else:
        res["plhiv"] = 0
        res["plhiv_q2"] = 0

    return res
