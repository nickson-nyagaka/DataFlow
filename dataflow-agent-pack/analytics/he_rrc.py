"""Health Education (Peer Education & Risk Reduction Counselling) indicator calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.common import any_in_unique_allrows
from core.compat import CompatSwitches
from core.periods import resolve_period_columns


def compute_he_rrc_indicators(
    df: pd.DataFrame, compat: CompatSwitches | None = None
) -> pd.DataFrame:
    """Computes Peer Education, RRC, and composite HE_RRC indicators on cleaned Register."""
    res = df.copy()
    lex_sort = compat.legacy_lexicographic_column_sort if compat else False
    case_insens = not compat.legacy_capitalize_vocabulary if compat else False

    # Peer Education
    pe_q1, pe_q2, _ = resolve_period_columns(
        res,
        r"received_peer_education_y_n_?\d*$",
        required=False,
        lexicographic_sort=lex_sort,
    )
    if pe_q1 or pe_q2:
        res["peereducation_q1"] = np.where(
            any_in_unique_allrows(res, pe_q1, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["peereducation_q2"] = np.where(
            any_in_unique_allrows(res, pe_q2, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["peereducation_sem"] = np.where(
            (res["peereducation_q1"] + res["peereducation_q2"]) >= 1, 1, 0
        )
    else:
        res["peereducation_q1"] = 0
        res["peereducation_q2"] = 0
        res["peereducation_sem"] = 0

    # RRC
    rrc_q1, rrc_q2, _ = resolve_period_columns(
        res,
        r"provided_with_risk_reduction_counselling_y_n_?\d*$",
        required=False,
        lexicographic_sort=lex_sort,
    )
    if rrc_q1 or rrc_q2:
        res["rrc_q1"] = np.where(
            any_in_unique_allrows(res, rrc_q1, ["Yes"], case_insensitive=case_insens), 1, 0
        )
        res["rrc_q2"] = np.where(
            any_in_unique_allrows(res, rrc_q2, ["Yes"], case_insensitive=case_insens), 1, 0
        )
    else:
        res["rrc_q1"] = 0
        res["rrc_q2"] = 0

    # HE_RRC composite
    res["he_rrc_q1"] = np.where((res["peereducation_q1"] == 1) | (res["rrc_q1"] == 1), 1, 0)
    res["he_rrc_q2"] = np.where((res["peereducation_q2"] == 1) | (res["rrc_q2"] == 1), 1, 0)

    return res
