"""Defined Package indicator calculations for DATAFLOW.

Implements two clinical pathways:
1. General Pathway: HTS + STI Screening + TB Screening + Condoms + HE/RRC (+ NSP for PWID per D-001/D-020).
2. PLHIV-Service Pathway: Known Positive (PLHIV) + STI Screening + TB Screening + Condoms + HE/RRC (+ NSP for PWID per D-020).
Composite Defined Package = General Pathway OR PLHIV-Service Pathway.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.compat import CompatSwitches
from core.config_models import PopulationConfig


def compute_defined_package_indicators(
    df: pd.DataFrame,
    population_config: PopulationConfig,
    compat: CompatSwitches | None = None,
) -> pd.DataFrame:
    """Computes Defined Package indicators driven by population config and compat switches."""
    if compat is None:
        compat = CompatSwitches()

    res = df.copy()

    # Determine if NSP is required
    if compat.legacy_comment_out_pwid_nsp:
        # Legacy notebook cell 61: NSP commented out across all populations
        require_nsp = False
    else:
        # Modern D-001 & D-020 (OQ-01): NSP required for PWID only in both pathways
        require_nsp = population_config.defined_package.require_nsp

    # ---------------------------------------------------------
    # Q1
    # ---------------------------------------------------------
    nsp_q1 = res["nsp_q1"] if "nsp_q1" in res.columns else 0
    general_nsp_q1 = (nsp_q1 == 1) if require_nsp else True
    plhiv_nsp_q1 = (nsp_q1 == 1) if require_nsp else True

    # PLHIV service pathway Q1
    res["plhivservice_q1"] = np.where(
        (res["plhiv"] == 1)
        & (res["sti_screened_q1"] == 1)
        & (res["condoms_q1"] == 1)
        & (res["he_rrc_q1"] == 1)
        & (res["tb_screened_q1"] == 1)
        & plhiv_nsp_q1,
        1,
        0,
    )

    # General pathway Q1
    general_pathway_q1 = (
        (res["hts_q1"] == 1)
        & (res["sti_screened_q1"] == 1)
        & (res["tb_screened_q1"] == 1)
        & (res["condoms_q1"] == 1)
        & (res["he_rrc_q1"] == 1)
        & general_nsp_q1
    )

    res["definedpackage_q1"] = np.where(
        general_pathway_q1 | (res["plhivservice_q1"] == 1),
        1,
        0,
    )

    # ---------------------------------------------------------
    # Q2
    # ---------------------------------------------------------
    nsp_q2 = res["nsp_q2"] if "nsp_q2" in res.columns else 0
    general_nsp_q2 = (nsp_q2 == 1) if require_nsp else True
    plhiv_nsp_q2 = (nsp_q2 == 1) if require_nsp else True

    # PLHIV service pathway Q2
    res["plhivservice_q2"] = np.where(
        (res["plhiv_q2"] == 1)
        & (res["sti_screened_q2"] == 1)
        & (res["condoms_q2"] == 1)
        & (res["he_rrc_q2"] == 1)
        & (res["tb_screened_q2"] == 1)
        & plhiv_nsp_q2,
        1,
        0,
    )

    # General pathway Q2
    general_pathway_q2 = (
        (res["hts_q2"] == 1)
        & (res["sti_screened_q2"] == 1)
        & (res["tb_screened_q2"] == 1)
        & (res["condoms_q2"] == 1)
        & (res["he_rrc_q2"] == 1)
        & general_nsp_q2
    )

    res["definedpackage_q2"] = np.where(
        general_pathway_q2 | (res["plhivservice_q2"] == 1),
        1,
        0,
    )

    # SEM
    res["definedpackage_sem"] = np.where(
        (res["definedpackage_q1"] + res["definedpackage_q2"]) >= 1, 1, 0
    )

    return res
