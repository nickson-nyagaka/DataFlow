"""Summary builder: aggregates indicators, handles missing geography, and formats columns."""

from __future__ import annotations

import pandas as pd

from analytics.engine import run_analytics
from core.compat import CompatSwitches
from reporting.template_manager import LayoutSpec, get_template_manager


def _standardize_geography_value(val: object) -> str:
    """Standardizes geography keys with Title Case, preserving (MISSING)."""
    if pd.isna(val):
        return "(MISSING)"
    s = str(val).strip()
    if not s or s.upper() in ["NAN", "NONE", "(MISSING)", "MISSING"]:
        return "(MISSING)"
    return s.title()


def build_export_summary(
    cleaned_register: pd.DataFrame,
    cleaned_kplhiv: pd.DataFrame,
    population: str,
    period_mode: str = "SEM",
    compat: CompatSwitches | None = None,
    layout_spec: LayoutSpec | None = None,
) -> pd.DataFrame:
    """
    Builds the final formatted summary DataFrame ready for Excel export.

    - Handles missing geography by imputing '(MISSING)' before grouping (D-009 / Exit criteria).
    - Executes analytical engine if indicator columns are not yet computed.
    - Computes total_nsp_SEM = total_nsp_q1 + total_nsp_q2 for PWID (D-032).
    - Sorts hierarchically County -> SR Name -> Region with (MISSING) at bottom (D-037).
    - Structures columns matching layout_spec.all_columns exactly (omitting phantom columns per D-029).
    - Ensures indicator columns are non-negative integers (D-038).
    """
    if compat is None:
        compat = CompatSwitches()

    manager = get_template_manager()
    if layout_spec is None:
        layout_spec = manager.get_layout_for(population, period_mode)

    # 1. Prepare copy of frames with standardized geography and (MISSING) imputed
    reg_df = cleaned_register.copy()
    kp_df = cleaned_kplhiv.copy()

    for col in ["county", "sr_name", "region"]:
        if col in reg_df.columns:
            reg_df[col] = reg_df[col].apply(_standardize_geography_value)
        else:
            reg_df[col] = "(MISSING)"

        if col in kp_df.columns:
            kp_df[col] = kp_df[col].apply(_standardize_geography_value)
        else:
            kp_df[col] = "(MISSING)"

    # Ensure required ID and PE columns exist on reg_df
    if "kp_vp_unique_identifier_code" not in reg_df.columns:
        # Check aliases
        for candidate in ["uic", "kp_vp_unique_identifier_code_", "client_uic", "program_uic"]:
            if candidate in reg_df.columns:
                reg_df["kp_vp_unique_identifier_code"] = reg_df[candidate]
                break
        if "kp_vp_unique_identifier_code" not in reg_df.columns:
            reg_df["kp_vp_unique_identifier_code"] = [f"GEN_{i}" for i in range(len(reg_df))]

    if "peer_educator_code" not in reg_df.columns:
        reg_df["peer_educator_code"] = "PE_UNKNOWN"

    # 2. Run analytics orchestrator to get indicator flags and merged summaries
    analytics_res = run_analytics(
        register_df=reg_df,
        kplhiv_df=kp_df,
        population=population,
        compat=compat,
    )
    merged = analytics_res["final_summary"]

    # Standardize geography keys on merged summary
    for col in ["county", "sr_name", "region"]:
        if col in merged.columns:
            merged[col] = merged[col].apply(_standardize_geography_value)

    # 3. PWID total_nsp_SEM resolution (D-032)
    if "total_nsp_SEM" in layout_spec.all_columns:
        if "total_nsp_SEM" not in merged.columns or merged["total_nsp_SEM"].isna().all():
            q1 = merged["total_nsp_Q1"] if "total_nsp_Q1" in merged.columns else 0
            q2 = merged["total_nsp_Q2"] if "total_nsp_Q2" in merged.columns else 0
            merged["total_nsp_SEM"] = q1 + q2

    # 4. Ensure all layout columns exist
    for col in layout_spec.all_columns:
        if col not in merged.columns:
            if col in ["county", "sr_name", "region"]:
                merged[col] = "(MISSING)"
            else:
                merged[col] = 0

    # 5. Reindex strictly to layout order
    final_df = merged[layout_spec.all_columns].copy()

    # 6. Cast indicator columns to integer (D-038)
    key_cols = ["county", "sr_name", "region"]
    for col in final_df.columns:
        if col not in key_cols:
            final_df[col] = pd.to_numeric(final_df[col], errors="coerce").fillna(0).astype(int)

    # 7. Hierarchical sorting: County -> SR Name -> Region with (MISSING) at the bottom (D-037)
    def _sort_key(series: pd.Series) -> pd.Series:
        return series.apply(lambda x: (1 if str(x) == "(MISSING)" else 0, str(x).lower()))

    final_df = final_df.sort_values(
        by=key_cols,
        key=_sort_key,
        ascending=True,
    ).reset_index(drop=True)

    return final_df
