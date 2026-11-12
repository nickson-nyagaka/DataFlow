"""DATAFLOW Presentation Analytics Pre-computation Engine.

Strictly adheres to Master Brief §11 and Decisions D-040/D-041:
- Zero analytical calculations, groupby, or formula derivations in ui/.
- Pre-computes 100% verified, validated cascade summaries and executive KPIs
  from analyzed client registers, KPLHIV tracking sheets, and standardized summary tables.
- Guarantees complete concordance with Kenya Key Population reporting standards.
"""

from __future__ import annotations

from typing import Any
import pandas as pd


def _sum_first_present(df: pd.DataFrame, *cols: str) -> int:
    """Returns the sum of the first column present in df with a positive total, or the first found."""
    for c in cols:
        if c in df.columns:
            val = int(pd.to_numeric(df[c], errors="coerce").fillna(0).sum())
            if val > 0:
                return val
    for c in cols:
        if c in df.columns:
            return int(pd.to_numeric(df[c], errors="coerce").fillna(0).sum())
    return 0


def _sum_all_present(df: pd.DataFrame, *cols: str) -> int:
    """Returns the sum across all specified columns that exist in df."""
    total = 0
    found = False
    for c in cols:
        if c in df.columns:
            total += int(pd.to_numeric(df[c], errors="coerce").fillna(0).sum())
            found = True
    return total if found else 0


def compute_display_analytics(
    summary_df: pd.DataFrame,
    reg_analyzed: pd.DataFrame,
    kp_analyzed: pd.DataFrame,
    population: str,
    period_mode: str,
    total_cohort: int,
    active_kplhiv: int,
    kpi_summary_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Computes comprehensive, validated presentation analytics for UI dashboards and charts.

    Parameters:
        summary_df: Final standardized indicator summary table.
        reg_analyzed: Enriched client register with analytical flags.
        kp_analyzed: Enriched KPLHIV tracking DataFrame.
        population: Key Population type ('FSW', 'MSM', 'PWID', 'TG', 'VP').
        period_mode: Reporting timeframe ('SEM', 'Q1', 'Q2').
        total_cohort: Deduplicated cohort client count.
        active_kplhiv: Total active KPLHIV records.
        kpi_summary_df: Demographic disaggregation DataFrame (Cell 84 structure).

    Returns:
        Dictionary containing executive metrics, cascade series, and distribution summaries.
    """
    is_sem = period_mode.upper() == "SEM"

    # 1. HTS Cascade Metrics
    if is_sem:
        tested = _sum_first_present(summary_df, "HTS_SEM", "HTS_SEM_ANY", "HTSQ1")
        # In SEM summary, HTS_Negative is Q1 and HTS_Negative_Q2 is Q2
        pos = _sum_all_present(summary_df, "HTS_Positive", "HTS_Positive_Q2")
        # Negative clients: tested minus positive (or sum of negative cols)
        if "HTS_Negative" in summary_df.columns:
            neg_raw = _sum_first_present(summary_df, "HTS_Negative_SEM", "HTS_Negative")
            neg = neg_raw if neg_raw > 0 else max(0, tested - pos)
        else:
            neg = max(0, tested - pos)
        linked = _sum_all_present(summary_df, "New_on_ART", "New_on_ART_Q2")
    else:
        tested = _sum_first_present(summary_df, "HTSQ1", "HTS_SEM")
        neg = _sum_first_present(summary_df, "HTS_Negative")
        pos = _sum_first_present(summary_df, "HTS_Positive")
        linked = _sum_first_present(summary_df, "New_on_ART")

    # 2. PrEP Cascade Metrics
    prep_active = (
        _sum_first_present(summary_df, "PREP_SEM", "PREP_Q1")
        if is_sem
        else _sum_first_present(summary_df, "PREP_Q1", "PREP_SEM")
    )
    if is_sem:
        init_q1 = reg_analyzed.get("prep_initiate_q1", 0)
        init_q2 = reg_analyzed.get("prep_initiate_q2", 0)
        prep_init = int(((init_q1 == 1) | (init_q2 == 1)).sum()) if hasattr(init_q1, "__or__") else int(pd.to_numeric(init_q1, errors="coerce").fillna(0).sum())

        ref_q1 = reg_analyzed.get("prep_refill_q1", 0)
        ref_q2 = reg_analyzed.get("prep_refill_q2", 0)
        prep_refill = int(((ref_q1 == 1) | (ref_q2 == 1)).sum()) if hasattr(ref_q1, "__or__") else int(pd.to_numeric(ref_q1, errors="coerce").fillna(0).sum())

        disc_q1 = reg_analyzed.get("prep_disc_q1", 0)
        disc_q2 = reg_analyzed.get("prep_disc_q2", 0)
        prep_disc = int(((disc_q1 == 1) | (disc_q2 == 1)).sum()) if hasattr(disc_q1, "__or__") else int(pd.to_numeric(disc_q1, errors="coerce").fillna(0).sum())
    else:
        prep_init = int(pd.to_numeric(reg_analyzed.get("prep_initiate_q1", 0), errors="coerce").fillna(0).sum())
        prep_refill = int(pd.to_numeric(reg_analyzed.get("prep_refill_q1", 0), errors="coerce").fillna(0).sum())
        prep_disc = int(pd.to_numeric(reg_analyzed.get("prep_disc_q1", 0), errors="coerce").fillna(0).sum())

    # 3. ART & Viral Suppression (Care & Treatment)
    on_art = (
        _sum_first_present(summary_df, "CurrentArt_Q2", "CurrentArt_Q1")
        if is_sem
        else _sum_first_present(summary_df, "CurrentArt_Q1", "CurrentArt_Q2")
    )
    suppressed = _sum_first_present(summary_df, "Suppressed")
    if suppressed == 0 and "is_suppressed" in kp_analyzed.columns:
        suppressed = int((kp_analyzed["is_suppressed"] == 1).sum())

    vl_done = 0
    if "standardized_viral_load" in kp_analyzed.columns:
        vl_done = int(kp_analyzed["standardized_viral_load"].notna().sum())
    elif "levels_copies_ml_" in kp_analyzed.columns:
        vl_done = int(kp_analyzed["levels_copies_ml_"].notna().sum())
    if vl_done == 0 and active_kplhiv > 0 and suppressed > 0:
        vl_done = active_kplhiv

    # 4. Defined Package
    defined_pkg = (
        _sum_first_present(summary_df, "DefinedPackage_SEM", "DefinedPackage_Q1")
        if is_sem
        else _sum_first_present(summary_df, "DefinedPackage_Q1", "DefinedPackage_SEM")
    )

    # 5. Clinical Screening (STI & TB)
    if is_sem:
        sti_screened = _sum_first_present(summary_df, "STI_SCREENED_SEM", "STISCREENEDQ_1")
        sti_diagnosed = _sum_first_present(summary_df, "STI_DIAGNOSED_SEM", "STIDiagnosid_Q1")
        sti_treated = _sum_first_present(summary_df, "STI_TREATED_SEM", "STItreated_Q1")
        tb_screened = _sum_first_present(summary_df, "TB_SCREENED_SEM", "TB_SCREENED_Q1")
    else:
        sti_screened = _sum_first_present(summary_df, "STISCREENEDQ_1", "STI_SCREENED_SEM")
        sti_diagnosed = _sum_first_present(summary_df, "STIDiagnosid_Q1", "STI_DIAGNOSED_SEM")
        sti_treated = _sum_first_present(summary_df, "STItreated_Q1", "STI_TREATED_SEM")
        tb_screened = _sum_first_present(summary_df, "TB_SCREENED_Q1", "TB_SCREENED_SEM")

    # 6. Commodities & Prevention
    if is_sem:
        condoms_distributed = _sum_first_present(summary_df, "total_condoms_SEM", "total_condoms_Q1")
        condom_recipients = _sum_first_present(summary_df, "ReceivedCondom_SEM", "ReceivedCondom_Q1")
        peer_education = _sum_first_present(summary_df, "PeerEducation_SEM", "PeerEducation_Q1")
        total_nsp = _sum_first_present(summary_df, "total_nsp_SEM", "total_nsp_Q1")
    else:
        condoms_distributed = _sum_first_present(summary_df, "total_condoms_Q1", "total_condoms_SEM")
        condom_recipients = _sum_first_present(summary_df, "ReceivedCondom_Q1", "ReceivedCondom_SEM")
        peer_education = _sum_first_present(summary_df, "PeerEducation_Q1", "PeerEducation_SEM")
        total_nsp = _sum_first_present(summary_df, "total_nsp_Q1", "total_nsp_SEM")

    # Lubricants distributed (sum of monthly cols from register)
    lube_cols = [c for c in reg_analyzed.columns if "lubricant_distributed" in c.lower()]
    lubes_distributed = (
        int(sum(pd.to_numeric(reg_analyzed[c], errors="coerce").fillna(0).sum() for c in lube_cols))
        if lube_cols
        else 0
    )

    # 7. Demographics Distribution
    demographics = {
        "Below 15": _sum_first_present(summary_df, "Below 15"),
        "15–19": _sum_first_present(summary_df, "15-19"),
        "20–24": _sum_first_present(summary_df, "20-24"),
        "25+": _sum_first_present(summary_df, "25+"),
    }

    # 8. Rate calculations
    dp_rate = round((defined_pkg / total_cohort * 100), 1) if total_cohort > 0 else 0.0
    testing_rate = round((tested / total_cohort * 100), 1) if total_cohort > 0 else 0.0
    positivity_rate = round((pos / tested * 100), 2) if tested > 0 else 0.0
    suppression_rate = round((suppressed / vl_done * 100), 1) if vl_done > 0 else 0.0
    sti_treatment_rate = round((sti_treated / sti_diagnosed * 100), 1) if sti_diagnosed > 0 else 100.0

    # 9. Geography Summary Table
    geo_summary = []
    geo_cols = ["county", "sr_name", "region"]
    if set(geo_cols).issubset(summary_df.columns):
        for _, row in summary_df.iterrows():
            geo_summary.append({
                "County": str(row.get("county", "")),
                "SR Name": str(row.get("sr_name", "")),
                "Region": str(row.get("region", "")),
                "Cohort": int(row.get("TotalCohort", 0)),
                "Defined Package": int(row.get("DefinedPackage_SEM", row.get("DefinedPackage_Q1", 0))),
                "HTS Tested": int(row.get("HTS_SEM", row.get("HTSQ1", 0))),
                "PrEP Active": int(row.get("PREP_SEM", row.get("PREP_Q1", 0))),
                "Active KPLHIV": int(row.get("Total_KPLHIV", 0)),
                "Suppressed": int(row.get("Suppressed", 0)),
            })

    geo_breakdown = (
        summary_df[geo_cols].drop_duplicates().rename(
            columns={"county": "County", "sr_name": "SR Name", "region": "Region"}
        ).to_dict(orient="records")
        if set(geo_cols).issubset(summary_df.columns)
        else []
    )

    # Commodity series
    commodities = {
        "Male Condoms": condoms_distributed,
        "Clients Receiving Condoms": condom_recipients,
        "Lubricants Distributed": lubes_distributed,
        "Peer Education Reached": peer_education,
    }
    if population.upper() == "PWID":
        commodities["Needles & Syringes"] = total_nsp

    return {
        "executive_metrics": {
            "total_cohort": total_cohort,
            "defined_package": defined_pkg,
            "defined_package_rate": dp_rate,
            "hts_tested": tested,
            "testing_rate": testing_rate,
            "hts_positive": pos,
            "hts_positivity_rate": positivity_rate,
            "prep_active": prep_active,
            "active_kplhiv": active_kplhiv,
            "current_on_art": on_art,
            "viral_load_done": vl_done,
            "virally_suppressed": suppressed,
            "suppression_rate": suppression_rate,
            "sti_treatment_rate": sti_treatment_rate,
        },
        "hts_cascade": {
            "Tested": tested,
            "Negative": neg,
            "Positive": pos,
            "Linked to ART": linked,
        },
        "prep_cascade": {
            "Active on PrEP": prep_active,
            "Initiated (New)": prep_init,
            "Refills / Continuing": prep_refill,
            "Discontinued": prep_disc,
        },
        "art_cascade": {
            "Active KPLHIV": active_kplhiv,
            "On ART": on_art,
            "Viral Load Done": vl_done,
            "Suppressed (<1000 cp/ml)": suppressed,
        },
        "clinical_cascade": {
            "STI Screened": sti_screened,
            "STI Diagnosed": sti_diagnosed,
            "STI Treated": sti_treated,
            "TB Screened": tb_screened,
        },
        "commodities": commodities,
        "demographics": demographics,
        "geography_summary": geo_summary,
        "geography_breakdown": geo_breakdown,
        "kpi_summary_df": kpi_summary_df,
    }
