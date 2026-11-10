"""Analytical Engine orchestrator for DATAFLOW.

Executes all indicator calculations across Register and KPLHIV datasets, supporting both
legacy bug-compatible mode and modern corrected mode via CompatSwitches.
"""

from __future__ import annotations

import pandas as pd

from analytics.art import compute_art_indicators
from analytics.condoms import compute_condom_indicators
from analytics.defined_package import compute_defined_package_indicators
from analytics.demographics import compute_age_group_counts
from analytics.he_rrc import compute_he_rrc_indicators
from analytics.hts import compute_hts_indicators
from analytics.kplhiv import compute_kplhiv_summary, process_kplhiv_frame
from analytics.nsp import compute_nsp_indicators
from analytics.prep import compute_prep_indicators
from analytics.sti import compute_sti_indicators
from analytics.summaries import build_register_summary, merge_final_summary
from analytics.tb import compute_tb_indicators
from core.compat import CompatSwitches
from core.config_models import PopulationConfig, load_population_config


def run_analytics(
    register_df: pd.DataFrame,
    kplhiv_df: pd.DataFrame | None = None,
    population: str = "FSW",
    population_config: PopulationConfig | None = None,
    compat: CompatSwitches | None = None,
) -> dict[str, pd.DataFrame]:
    """Runs the analytical pipeline on cleaned Register and KPLHIV DataFrames.

    Returns:
        dict containing:
        - "final_summary": merged summary frame (county x sr_name x region)
        - "summary_fsw" / "summary_register": register summary metrics
        - "summary_kplhiv": KPLHIV summary metrics
        - "age_group_counts": demographic pivot table
        - "cleaned_register": register frame with all 88 indicator columns populated
        - "cleaned_kplhiv": processed KPLHIV frame with standardized viral loads
    """
    if compat is None:
        compat = CompatSwitches()

    if population_config is None:
        population_config = load_population_config(population)

    if kplhiv_df is None:
        kplhiv_df = pd.DataFrame()

    # 1. Pipeline execution on Register frame
    reg = register_df.copy()

    # PrEP
    reg = compute_prep_indicators(reg, compat=compat)

    # HTS
    reg = compute_hts_indicators(reg, compat=compat)

    # ART & PLHIV
    reg = compute_art_indicators(reg, compat=compat)

    # STI
    reg = compute_sti_indicators(reg, compat=compat)

    # TB
    reg = compute_tb_indicators(reg, compat=compat)

    # Peer Education & RRC
    reg = compute_he_rrc_indicators(reg, compat=compat)

    # Condoms
    reg = compute_condom_indicators(reg, compat=compat)

    # NSP (PWID)
    reg = compute_nsp_indicators(reg, compat=compat)

    # Defined Package
    reg = compute_defined_package_indicators(reg, population_config, compat=compat)

    # 2. Pipeline execution on KPLHIV frame
    kp = process_kplhiv_frame(kplhiv_df, compat=compat)
    summary_kp = compute_kplhiv_summary(kp)

    # 3. Demographic pivots
    age_counts = compute_age_group_counts(reg, compat=compat)

    # 4. Register summary
    summary_reg = build_register_summary(reg, compat=compat)

    # 5. Final summary merge
    final_summary = merge_final_summary(summary_reg, summary_kp, age_counts)

    return {
        "final_summary": final_summary,
        "summary_register": summary_reg,
        "summary_fsw": summary_reg,
        "summary_kplhiv": summary_kp,
        "age_group_counts": age_counts,
        "cleaned_register": reg,
        "cleaned_kplhiv": kp,
    }
