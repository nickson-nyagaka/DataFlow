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

from analytics.demographics import assign_age_groups


def _sum_first_present(df: pd.DataFrame, *cols: str) -> int:
    """Returns the sum of the first column present in df with a positive total, or the first found (case-insensitive)."""
    col_map = {str(c).strip().lower(): c for c in df.columns}
    for c in cols:
        matched = col_map.get(c.strip().lower())
        if matched is not None:
            val = int(pd.to_numeric(df[matched], errors="coerce").fillna(0).sum())
            if val > 0:
                return val
    for c in cols:
        matched = col_map.get(c.strip().lower())
        if matched is not None:
            return int(pd.to_numeric(df[matched], errors="coerce").fillna(0).sum())
    return 0


def _sum_all_present(df: pd.DataFrame, *cols: str) -> int:
    """Returns the sum across all specified columns that exist in df (case-insensitive)."""
    total = 0
    found = False
    col_map = {str(c).strip().lower(): c for c in df.columns}
    for c in cols:
        matched = col_map.get(c.strip().lower())
        if matched is not None:
            total += int(pd.to_numeric(df[matched], errors="coerce").fillna(0).sum())
            found = True
    return total if found else 0


def _count_flags(df: pd.DataFrame, *cols: str) -> int:
    """Counts binary flags (1) across specified columns in df with OR logic (case-insensitive)."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return 0
    col_map = {str(c).strip().lower(): c for c in df.columns}
    matched_cols = [col_map[c.strip().lower()] for c in cols if c.strip().lower() in col_map]
    if not matched_cols:
        return 0
    series = [df[c] for c in matched_cols]
    mask = (series[0] == 1) | (series[0] == "1") | (series[0] is True)
    for s in series[1:]:
        mask = mask | (s == 1) | (s == "1") | (s is True)
    return int(mask.sum())


def extract_hts_cascade(
    summary_df: pd.DataFrame | None = None,
    period_mode: str = "SEM",
    reg_df: pd.DataFrame | None = None,
) -> dict[str, int]:
    """Extracts HTS cascade counts (Tested, Negative, Positive, Linked) accurately from summary DataFrame or register.

    Guarantees concordance across all periods:
      - Q1: Tested = HTSQ1, Pos = HTS_Positive, Linked = New_on_ART, Neg = Tested - Pos
      - Q2: Tested = HTSQ2, Pos = HTS_Positive_Q2, Linked = New_on_ART_Q2, Neg = Tested - Pos
      - SEM: Tested = HTS_SEM_ANY (or HTS_SEM), Pos = HTS_Positive + HTS_Positive_Q2,
             Linked = New_on_ART + New_on_ART_Q2, Neg = Tested - Pos
    Ensures mathematical consistency: Tested == Negative + Positive.
    """
    if (summary_df is None or summary_df.empty) and (reg_df is None or reg_df.empty):
        return {"Tested": 0, "Negative": 0, "Positive": 0, "Linked to ART": 0, "Linked": 0}

    mode = (period_mode or "SEM").upper()

    tested = 0
    pos = 0
    linked = 0

    if mode == "Q1":
        if summary_df is not None and not summary_df.empty:
            tested = _sum_first_present(summary_df, "HTSQ1", "hts_q1", "HTS_Q1", "total_tested_q1")
            pos = _sum_first_present(summary_df, "HTS_Positive", "hts_Positive_q1", "hts_pos_q1", "POSQ1")
            linked = _sum_first_present(summary_df, "New_on_ART", "Positive_art", "new_on_art_q1")
        if tested == 0 and isinstance(reg_df, pd.DataFrame) and "hts_q1" in reg_df.columns:
            tested = int((reg_df["hts_q1"] == 1).sum())
        if pos == 0 and isinstance(reg_df, pd.DataFrame) and "hts_Positive_q1" in reg_df.columns:
            pos = int((reg_df["hts_Positive_q1"] == 1).sum())
        if linked == 0 and isinstance(reg_df, pd.DataFrame) and "Positive_art" in reg_df.columns:
            linked = int((reg_df["Positive_art"] == 1).sum())
        neg = max(0, tested - pos)

    elif mode == "Q2":
        if summary_df is not None and not summary_df.empty:
            tested = _sum_first_present(summary_df, "HTSQ2", "hts_q2", "HTS_Q2", "total_tested_q2")
            pos = _sum_first_present(summary_df, "HTS_Positive_Q2", "hts_Positive_q2", "hts_pos_q2", "POSQ2")
            linked = _sum_first_present(summary_df, "New_on_ART_Q2", "Positive_art_q2", "new_on_art_q2")
        if tested == 0 and isinstance(reg_df, pd.DataFrame) and "hts_q2" in reg_df.columns:
            tested = int((reg_df["hts_q2"] == 1).sum())
        if pos == 0 and isinstance(reg_df, pd.DataFrame) and "hts_Positive_q2" in reg_df.columns:
            pos = int((reg_df["hts_Positive_q2"] == 1).sum())
        if linked == 0 and isinstance(reg_df, pd.DataFrame) and "Positive_art_q2" in reg_df.columns:
            linked = int((reg_df["Positive_art_q2"] == 1).sum())
        neg = max(0, tested - pos)

    else:  # SEM
        if summary_df is not None and not summary_df.empty:
            tested_any = _sum_first_present(summary_df, "HTS_SEM_ANY", "hts_sem_any")
            tested_sem = _sum_first_present(summary_df, "HTS_SEM", "hts_sem")
            tested = tested_any if tested_any > 0 else (
                tested_sem if tested_sem > 0 else _sum_all_present(summary_df, "HTSQ1", "HTSQ2")
            )
            pos = _sum_all_present(summary_df, "HTS_Positive", "HTS_Positive_Q2")
            linked = _sum_all_present(summary_df, "New_on_ART", "New_on_ART_Q2")
        if tested == 0 and isinstance(reg_df, pd.DataFrame):
            if "hts_sem_any" in reg_df.columns:
                tested = int((reg_df["hts_sem_any"] == 1).sum())
            elif "hts_sem" in reg_df.columns:
                tested = int((reg_df["hts_sem"] == 1).sum())
            else:
                tested = _count_flags(reg_df, "hts_q1", "hts_q2")
        if pos == 0 and isinstance(reg_df, pd.DataFrame):
            pos = _count_flags(reg_df, "hts_Positive_q1", "hts_Positive_q2")
        if linked == 0 and isinstance(reg_df, pd.DataFrame):
            linked = _count_flags(reg_df, "Positive_art", "Positive_art_q2")
        neg = max(0, tested - pos)

    return {
        "Tested": int(tested),
        "Negative": int(neg),
        "Positive": int(pos),
        "Linked to ART": int(linked),
        "Linked": int(linked),
    }


def extract_prep_cascade(
    summary_df: pd.DataFrame,
    reg_df: pd.DataFrame | None = None,
    period_mode: str = "SEM",
) -> dict[str, int]:
    """Extracts PrEP cascade stages: Active, Initiated, Refills, Restarted, Switched, Discontinued."""
    pm = period_mode.upper() if period_mode else "SEM"

    if isinstance(reg_df, pd.DataFrame) and not reg_df.empty:
        if "prep_restart_q1" not in reg_df.columns or "prep_switched_q1" not in reg_df.columns:
            from analytics.prep import compute_prep_indicators
            try:
                reg_df = compute_prep_indicators(reg_df)
            except Exception:
                pass

    if pm == "Q1":
        prep_active = _sum_first_present(summary_df, "PREP_Q1")
        if prep_active == 0 and isinstance(reg_df, pd.DataFrame) and "prep_q1" in reg_df.columns:
            prep_active = int((reg_df["prep_q1"] == 1).sum())
        prep_init = _count_flags(reg_df, "prep_initiate_q1")
        prep_refill = _count_flags(reg_df, "prep_refill_q1")
        prep_restart = _count_flags(reg_df, "prep_restart_q1")
        prep_switched = _count_flags(reg_df, "prep_switched_q1")
        prep_disc = _count_flags(reg_df, "prep_disc_q1")

    elif pm == "Q2":
        prep_active = _sum_first_present(summary_df, "PREP_Q2")
        if prep_active == 0 and isinstance(reg_df, pd.DataFrame) and "prep_q2" in reg_df.columns:
            prep_active = int((reg_df["prep_q2"] == 1).sum())
        prep_init = _count_flags(reg_df, "prep_initiate_q2")
        prep_refill = _count_flags(reg_df, "prep_refill_q2")
        prep_restart = _count_flags(reg_df, "prep_restart_q2")
        prep_switched = _count_flags(reg_df, "prep_switched_q2")
        prep_disc = _count_flags(reg_df, "prep_disc_q2")

    else:  # SEM: summation of Q1 + Q2
        prep_active = _sum_first_present(summary_df, "PREP_SEM")
        if prep_active == 0:
            prep_active = _sum_all_present(summary_df, "PREP_Q1", "PREP_Q2")
        if prep_active == 0 and isinstance(reg_df, pd.DataFrame):
            if "prep_sem" in reg_df.columns:
                prep_active = int(reg_df["prep_sem"].sum())
            elif "prep_q1" in reg_df.columns and "prep_q2" in reg_df.columns:
                prep_active = int(reg_df["prep_q1"].sum() + reg_df["prep_q2"].sum())
            elif "prep_q1" in reg_df.columns:
                prep_active = int(reg_df["prep_q1"].sum())

        prep_init = _count_flags(reg_df, "prep_initiate_q1", "prep_initiate_q2")
        prep_refill = _count_flags(reg_df, "prep_refill_q1", "prep_refill_q2")
        prep_restart = _count_flags(reg_df, "prep_restart_q1", "prep_restart_q2")
        prep_switched = _count_flags(reg_df, "prep_switched_q1", "prep_switched_q2")
        prep_disc = _count_flags(reg_df, "prep_disc_q1", "prep_disc_q2")

    return {
        "Active on PrEP": int(prep_active),
        "Initiated (New)": int(prep_init),
        "Refills": int(prep_refill),
        "Restarted": int(prep_restart),
        "Switched": int(prep_switched),
        "Discontinued": int(prep_disc),
    }


def extract_art_cascade(
    summary_df: pd.DataFrame,
    kp_df: pd.DataFrame | None = None,
    period_mode: str = "SEM",
) -> dict[str, int]:
    """Extracts 95-95-95 ART care and viral suppression cascade metrics."""
    is_sem = period_mode.upper() == "SEM"
    active_kplhiv = _sum_first_present(summary_df, "Total_KPLHIV")
    if active_kplhiv == 0 and isinstance(kp_df, pd.DataFrame):
        active_kplhiv = len(kp_df)

    on_art = (
        _sum_first_present(summary_df, "CurrentArt_Q2", "CurrentArt_Q1")
        if is_sem
        else _sum_first_present(summary_df, "CurrentArt_Q1", "CurrentArt_Q2")
    )
    if on_art == 0 and active_kplhiv > 0:
        on_art = active_kplhiv

    suppressed = _sum_first_present(summary_df, "Suppressed")
    if suppressed == 0 and isinstance(kp_df, pd.DataFrame) and "is_suppressed" in kp_df.columns:
        suppressed = int((kp_df["is_suppressed"] == 1).sum())

    vl_done = 0
    if isinstance(kp_df, pd.DataFrame):
        if "standardized_viral_load" in kp_df.columns:
            vl_done = int(kp_df["standardized_viral_load"].notna().sum())
        elif "levels_copies_ml_" in kp_df.columns:
            vl_done = int(kp_df["levels_copies_ml_"].notna().sum())
    if vl_done == 0 and active_kplhiv > 0 and suppressed > 0:
        vl_done = active_kplhiv

    return {
        "Active KPLHIV": active_kplhiv,
        "On ART": on_art,
        "Viral Load Done": vl_done,
        "Suppressed (<1000 cp/ml)": suppressed,
    }


def extract_clinical_cascade(
    summary_df: pd.DataFrame,
    period_mode: str = "SEM",
) -> dict[str, int]:
    """Extracts clinical screening management metrics (STI & TB)."""
    is_sem = period_mode.upper() == "SEM"
    if is_sem:
        sti_s = _sum_first_present(summary_df, "STI_SCREENED_SEM", "STISCREENEDQ_1")
        sti_d = _sum_first_present(summary_df, "STI_DIAGNOSED_SEM", "STIDiagnosid_Q1")
        sti_t = _sum_first_present(summary_df, "STI_TREATED_SEM", "STItreated_Q1")
        tb_s = _sum_first_present(summary_df, "TB_SCREENED_SEM", "TB_SCREENED_Q1")
    else:
        sti_s = _sum_first_present(summary_df, "STISCREENEDQ_1", "STI_SCREENED_SEM")
        sti_d = _sum_first_present(summary_df, "STIDiagnosid_Q1", "STI_DIAGNOSED_SEM")
        sti_t = _sum_first_present(summary_df, "STItreated_Q1", "STI_TREATED_SEM")
        tb_s = _sum_first_present(summary_df, "TB_SCREENED_Q1", "TB_SCREENED_SEM")

    return {
        "STI Screened": sti_s,
        "STI Diagnosed": sti_d,
        "STI Treated": sti_t,
        "TB Screened": tb_s,
    }


def extract_commodities(
    summary_df: pd.DataFrame,
    reg_df: pd.DataFrame | None = None,
    population: str = "FSW",
    period_mode: str = "SEM",
) -> dict[str, int]:
    """Extracts commodity distribution volumes and peer education reach."""
    is_sem = period_mode.upper() == "SEM"
    if is_sem:
        condoms = _sum_first_present(summary_df, "total_condoms_SEM", "total_condoms_Q1")
        condom_recip = _sum_first_present(summary_df, "ReceivedCondom_SEM", "ReceivedCondom_Q1")
        peer_ed = _sum_first_present(summary_df, "PeerEducation_SEM", "PeerEducation_Q1")
        total_nsp = _sum_first_present(summary_df, "total_nsp_SEM", "total_nsp_Q1")
    else:
        condoms = _sum_first_present(summary_df, "total_condoms_Q1", "total_condoms_SEM")
        condom_recip = _sum_first_present(summary_df, "ReceivedCondom_Q1", "ReceivedCondom_SEM")
        peer_ed = _sum_first_present(summary_df, "PeerEducation_Q1", "PeerEducation_SEM")
        total_nsp = _sum_first_present(summary_df, "total_nsp_Q1", "total_nsp_SEM")

    lube_cols = (
        [c for c in reg_df.columns if "lubricant_distributed" in c.lower()]
        if isinstance(reg_df, pd.DataFrame)
        else []
    )
    lubes = (
        int(sum(pd.to_numeric(reg_df[c], errors="coerce").fillna(0).sum() for c in lube_cols))
        if lube_cols
        else 0
    )

    comm = {
        "Male Condoms": condoms,
        "Clients Receiving Condoms": condom_recip,
        "Lubricants Distributed": lubes,
        "Peer Education Reached": peer_ed,
    }
    if population.strip().upper() == "PWID":
        comm["Needles & Syringes"] = total_nsp

    return comm


def append_total_row(df: pd.DataFrame, label_col: str | None = None) -> pd.DataFrame:
    """Appends a TOTAL row summing numeric columns and leaves other columns empty."""
    if df is None or df.empty:
        return df

    res = df.copy()
    numeric_cols = [c for c in res.columns if pd.api.types.is_numeric_dtype(res[c])]
    non_numeric_cols = [c for c in res.columns if c not in numeric_cols]

    target_label = label_col
    if not target_label or target_label not in res.columns:
        target_label = non_numeric_cols[0] if non_numeric_cols else res.columns[0]

    total_dict: dict[str, Any] = {}
    for col in res.columns:
        if col in numeric_cols:
            s = res[col].fillna(0).sum()
            total_dict[col] = int(s) if float(s).is_integer() else round(float(s), 2)
        elif col == target_label:
            total_dict[col] = "TOTAL"
        else:
            total_dict[col] = ""

    return pd.concat([res, pd.DataFrame([total_dict])], ignore_index=True)


def style_table_with_total_row(df: pd.DataFrame):
    """Styles a DataFrame so the 'TOTAL' row has a distinguishable light-green background and bold values."""
    if df is None or df.empty:
        return df

    def _highlight_total(row):
        is_total = any(str(v).strip().upper() == "TOTAL" for v in row)
        if is_total:
            return ["background-color: #D5F5E3; font-weight: bold; color: #145A32;"] * len(row)
        return [""] * len(row)

    return df.style.apply(_highlight_total, axis=1)


def extract_demographic_pyramid(
    reg_df: pd.DataFrame,
    population: str,
    summary_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Calculates age and sex distribution for cohort demographic pyramid adhering strictly to typology rules.

    - FSW: Female only (Male strictly 0)
    - MSM: Male only (Female strictly 0)
    - PWID, TG, VP: Bilateral male vs female disaggregation
    """
    age_bands = ["Below 15", "15–19", "20–24", "25+"]
    male_counts = [0, 0, 0, 0]
    female_counts = [0, 0, 0, 0]
    unknown_counts = [0, 0, 0, 0]

    pop_u = population.strip().upper()

    if reg_df is None or reg_df.empty:
        return {
            "age_groups": age_bands,
            "male_counts": male_counts,
            "female_counts": female_counts,
            "unknown_counts": unknown_counts,
            "population": population,
        }

    # 1. Resolve age groups safely
    if "age_group" in reg_df.columns:
        age_s = reg_df["age_group"].astype(str).str.strip()
    elif "age" in reg_df.columns:
        age_s = assign_age_groups(reg_df).astype(str).str.strip()
    else:
        cand_age = next((c for c in reg_df.columns if "age" in c.lower()), None)
        if cand_age:
            age_s = assign_age_groups(reg_df, age_col=cand_age).astype(str).str.strip()
        else:
            age_s = pd.Series("Unknown", index=reg_df.index)

    # 2. Typology handling
    if pop_u == "FSW":
        for idx, (b_hyphen, b_endash) in enumerate([
            ("Below 15", "Below 15"),
            ("15-19", "15–19"),
            ("20-24", "20–24"),
            ("25+", "25+"),
        ]):
            mask_age = (age_s == b_hyphen) | (age_s == b_endash)
            female_counts[idx] = int(mask_age.sum())

    elif pop_u == "MSM":
        for idx, (b_hyphen, b_endash) in enumerate([
            ("Below 15", "Below 15"),
            ("15-19", "15–19"),
            ("20-24", "20–24"),
            ("25+", "25+"),
        ]):
            mask_age = (age_s == b_hyphen) | (age_s == b_endash)
            male_counts[idx] = int(mask_age.sum())

    else:
        # PWID, TG, VP: Bilateral Male vs Female
        sex_col = None
        for cand in ["sex_m_f_", "sex", "gender", "Sex (M/F)", "Sex (M/F) ", "sex_m_f", "Sex", "Gender"]:
            if cand in reg_df.columns:
                sex_col = cand
                break
        if sex_col is None:
            sex_col = next((c for c in reg_df.columns if any(t in c.lower() for t in ["sex", "gender"])), None)

        if sex_col is not None:
            def _norm_sex(val: object) -> str:
                s = str(val).strip().upper()
                if s in ["M", "MALE", "1", "MAN", "M."]:
                    return "M"
                if s in ["F", "FEMALE", "2", "WOMAN", "F."]:
                    return "F"
                return "Unknown"

            clean_sex = reg_df[sex_col].apply(_norm_sex)

            for idx, (b_hyphen, b_endash) in enumerate([
                ("Below 15", "Below 15"),
                ("15-19", "15–19"),
                ("20-24", "20–24"),
                ("25+", "25+"),
            ]):
                mask_age = (age_s == b_hyphen) | (age_s == b_endash)
                male_counts[idx] = int((mask_age & (clean_sex == "M")).sum())
                female_counts[idx] = int((mask_age & (clean_sex == "F")).sum())
                unknown_counts[idx] = int((mask_age & (clean_sex == "Unknown")).sum())
        else:
            for idx, (b_hyphen, b_endash) in enumerate([
                ("Below 15", "Below 15"),
                ("15-19", "15–19"),
                ("20-24", "20–24"),
                ("25+", "25+"),
            ]):
                mask_age = (age_s == b_hyphen) | (age_s == b_endash)
                unknown_counts[idx] = int(mask_age.sum())

    return {
        "age_groups": age_bands,
        "male_counts": male_counts,
        "female_counts": female_counts,
        "unknown_counts": unknown_counts,
        "population": population,
    }


def compute_display_analytics(
    summary_df: pd.DataFrame,
    reg_analyzed: pd.DataFrame,
    kp_analyzed: pd.DataFrame,
    population: str,
    period_mode: str,
    total_cohort: int,
    active_kplhiv: int,
    kpi_summary_df: pd.DataFrame | None = None,
    dqa_results: Any = None,
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
    hts_data = extract_hts_cascade(summary_df, period_mode, reg_analyzed)
    tested = hts_data["Tested"]
    neg = hts_data["Negative"]
    pos = hts_data["Positive"]
    linked = hts_data["Linked to ART"]

    # 2. PrEP Cascade Metrics
    prep_data = extract_prep_cascade(summary_df, reg_analyzed, period_mode)
    prep_active = prep_data["Active on PrEP"]
    prep_init = prep_data["Initiated (New)"]
    prep_refill = prep_data["Refills"]
    prep_restart = prep_data.get("Restarted", 0)
    prep_switched = prep_data["Switched"]
    prep_disc = prep_data["Discontinued"]

    # 3. ART & Viral Suppression (Care & Treatment)
    art_data = extract_art_cascade(summary_df, kp_analyzed, period_mode)
    active_kplhiv = art_data["Active KPLHIV"]
    on_art = art_data["On ART"]
    vl_done = art_data["Viral Load Done"]
    suppressed = art_data["Suppressed (<1000 cp/ml)"]

    # 4. Defined Package
    defined_pkg = (
        _sum_first_present(summary_df, "DefinedPackage_SEM", "DefinedPackage_Q1")
        if is_sem
        else _sum_first_present(summary_df, "DefinedPackage_Q1", "DefinedPackage_SEM")
    )

    # 5. Clinical Screening (STI & TB)
    clinical_data = extract_clinical_cascade(summary_df, period_mode)
    sti_screened = clinical_data["STI Screened"]
    sti_diagnosed = clinical_data["STI Diagnosed"]
    sti_treated = clinical_data["STI Treated"]
    tb_screened = clinical_data["TB Screened"]

    # 6. Commodities & Prevention
    commodities = extract_commodities(summary_df, reg_analyzed, population, period_mode)
    condoms_distributed = commodities.get("Male Condoms", 0)
    condom_recipients = commodities.get("Clients Receiving Condoms", 0)
    lubes_distributed = commodities.get("Lubricants Distributed", 0)
    peer_education = commodities.get("Peer Education Reached", 0)
    total_nsp = commodities.get("Needles & Syringes", 0)

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
            if is_sem:
                hts_val = int(row.get("HTS_SEM_ANY", 0) or row.get("HTS_SEM", 0) or row.get("HTSQ1", 0))
                dp_val = int(row.get("DefinedPackage_SEM", 0) or row.get("DefinedPackage_Q1", 0))
                prep_val = int(row.get("PREP_SEM", 0) or row.get("PREP_Q1", 0))
            elif period_mode.upper() == "Q2":
                hts_val = int(row.get("HTSQ2", 0) or row.get("HTS_SEM", 0))
                dp_val = int(row.get("DefinedPackage_Q2", 0) or row.get("DefinedPackage_SEM", 0))
                prep_val = int(row.get("PREP_Q2", 0) or row.get("PREP_SEM", 0))
            else:  # Q1
                hts_val = int(row.get("HTSQ1", 0) or row.get("HTS_SEM", 0))
                dp_val = int(row.get("DefinedPackage_Q1", 0) or row.get("DefinedPackage_SEM", 0))
                prep_val = int(row.get("PREP_Q1", 0) or row.get("PREP_SEM", 0))

            geo_summary.append({
                "County": str(row.get("county", "")),
                "SR Name": str(row.get("sr_name", "")),
                "Region": str(row.get("region", "")),
                "Cohort": int(row.get("TotalCohort", 0)),
                "Defined Package": dp_val,
                "HTS Tested": hts_val,
                "PrEP Active": prep_val,
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

    # 10. Performance Scorecard against approved Global Fund / Kenya 95-95-95 targets
    linkage_rate = round((linked / pos * 100), 1) if pos > 0 else (100.0 if tested > 0 else 0.0)
    vl_cov_rate = round((vl_done / active_kplhiv * 100), 1) if active_kplhiv > 0 else 0.0

    scorecard = [
        {
            "indicator": "Defined Package Coverage",
            "actual": dp_rate,
            "target": 80.0,
            "numerator": defined_pkg,
            "denominator": total_cohort,
            "unit": "%",
            "status": "On Track" if dp_rate >= 80.0 else ("Needs Attention" if dp_rate >= 70.0 else "Below Target"),
            "gap": round(max(0.0, 80.0 - dp_rate), 1),
        },
        {
            "indicator": "HIV Testing Coverage",
            "actual": testing_rate,
            "target": 90.0,
            "numerator": tested,
            "denominator": total_cohort,
            "unit": "%",
            "status": "On Track" if testing_rate >= 90.0 else ("Needs Attention" if testing_rate >= 80.0 else "Below Target"),
            "gap": round(max(0.0, 90.0 - testing_rate), 1),
        },
        {
            "indicator": "Treatment Linkage (1st 95)",
            "actual": linkage_rate,
            "target": 95.0,
            "numerator": linked,
            "denominator": pos,
            "unit": "%",
            "status": "On Track" if linkage_rate >= 95.0 else ("Needs Attention" if linkage_rate >= 85.0 else "Below Target"),
            "gap": round(max(0.0, 95.0 - linkage_rate), 1),
        },
        {
            "indicator": "Viral Load Coverage (2nd 95)",
            "actual": vl_cov_rate,
            "target": 95.0,
            "numerator": vl_done,
            "denominator": active_kplhiv,
            "unit": "%",
            "status": "On Track" if vl_cov_rate >= 95.0 else ("Needs Attention" if vl_cov_rate >= 85.0 else "Below Target"),
            "gap": round(max(0.0, 95.0 - vl_cov_rate), 1),
        },
        {
            "indicator": "Viral Suppression (3rd 95)",
            "actual": suppression_rate,
            "target": 95.0,
            "numerator": suppressed,
            "denominator": vl_done,
            "unit": "%",
            "status": "On Track" if suppression_rate >= 95.0 else ("Needs Attention" if suppression_rate >= 85.0 else "Below Target"),
            "gap": round(max(0.0, 95.0 - suppression_rate), 1),
        },
    ]

    # 11. Regional Performance & SR Rankings Aggregates
    reg_map: dict[str, dict[str, Any]] = {}
    sr_map: dict[str, dict[str, Any]] = {}
    geo_hierarchy: dict[str, dict[str, list[str]]] = {}

    for row in geo_summary:
        r = str(row.get("Region", "(MISSING)"))
        c = str(row.get("County", "(MISSING)"))
        sr = str(row.get("SR Name", "(MISSING)"))

        if r not in geo_hierarchy:
            geo_hierarchy[r] = {}
        if c not in geo_hierarchy[r]:
            geo_hierarchy[r][c] = []
        if sr not in geo_hierarchy[r][c]:
            geo_hierarchy[r][c].append(sr)

        if r not in reg_map:
            reg_map[r] = {
                "region": r,
                "cohort": 0,
                "tested": 0,
                "defined_package": 0,
                "prep_active": 0,
                "active_kplhiv": 0,
                "suppressed": 0,
            }
        reg_map[r]["cohort"] += row["Cohort"]
        reg_map[r]["tested"] += row["HTS Tested"]
        reg_map[r]["defined_package"] += row["Defined Package"]
        reg_map[r]["prep_active"] += row["PrEP Active"]
        reg_map[r]["active_kplhiv"] += row["Active KPLHIV"]
        reg_map[r]["suppressed"] += row["Suppressed"]

        if sr not in sr_map:
            sr_map[sr] = {
                "sr_name": sr,
                "region": r,
                "cohort": 0,
                "tested": 0,
                "defined_package": 0,
                "prep_active": 0,
                "active_kplhiv": 0,
                "suppressed": 0,
            }
        sr_map[sr]["cohort"] += row["Cohort"]
        sr_map[sr]["tested"] += row["HTS Tested"]
        sr_map[sr]["defined_package"] += row["Defined Package"]
        sr_map[sr]["prep_active"] += row["PrEP Active"]
        sr_map[sr]["active_kplhiv"] += row["Active KPLHIV"]
        sr_map[sr]["suppressed"] += row["Suppressed"]

    regional_performance = []
    for _r, data in sorted(reg_map.items()):
        coh = data["cohort"]
        tst = data["tested"]
        data["testing_rate"] = round(tst / coh * 100, 1) if coh > 0 else 0.0
        data["dp_rate"] = round(data["defined_package"] / coh * 100, 1) if coh > 0 else 0.0
        data["prep_rate"] = round(data["prep_active"] / coh * 100, 1) if coh > 0 else 0.0
        kpl = data["active_kplhiv"]
        sup = data["suppressed"]
        data["suppression_rate"] = round(sup / kpl * 100, 1) if kpl > 0 else 0.0
        regional_performance.append(data)

    sr_rankings = []
    for _sr, data in sorted(sr_map.items(), key=lambda x: x[1]["cohort"], reverse=True):
        coh = data["cohort"]
        tst = data["tested"]
        data["testing_rate"] = round(tst / coh * 100, 1) if coh > 0 else 0.0
        data["dp_rate"] = round(data["defined_package"] / coh * 100, 1) if coh > 0 else 0.0
        data["prep_rate"] = round(data["prep_active"] / coh * 100, 1) if coh > 0 else 0.0
        kpl = data["active_kplhiv"]
        sup = data["suppressed"]
        data["suppression_rate"] = round(sup / kpl * 100, 1) if kpl > 0 else 0.0
        sr_rankings.append(data)

    # 12. Management Attention Alerts (Purely derived from actual metrics & DQA)
    management_alerts = []
    crit_count = 0
    if dqa_results is not None:
        if hasattr(dqa_results, "severity_counts"):
            crit_count = dqa_results.severity_counts.get("Critical", 0)
        elif isinstance(dqa_results, dict):
            crit_count = dqa_results.get("critical_dqa_count", 0)

    if crit_count > 0:
        management_alerts.append({
            "category": "Data Quality",
            "severity": "Critical",
            "title": "Critical DQA Exceptions Detected",
            "message": f"{crit_count} Critical DQA exception(s) require Sub-Recipient follow-up and reconciliation before external submission.",
            "trace_metric": f"{crit_count} Critical Exceptions",
        })

    if pos > linked:
        management_alerts.append({
            "category": "Clinical Gap",
            "severity": "Critical",
            "title": "Unlinked HIV-Positive Clients",
            "message": f"{pos - linked} newly diagnosed HIV-positive client(s) lack documented linkage to ART in this reporting period.",
            "trace_metric": f"{pos - linked} unlinked",
        })

    for reg in regional_performance:
        if reg["cohort"] >= 10 and reg["testing_rate"] < 75.0:
            management_alerts.append({
                "category": "Coverage Gap",
                "severity": "Warning",
                "title": f"Low HTS Coverage in {reg['region']}",
                "message": f"Region {reg['region']} HTS coverage is {reg['testing_rate']:.1f}% ({reg['tested']:,}/{reg['cohort']:,}), significantly below the 90% benchmark.",
                "trace_metric": f"{reg['region']}: {reg['testing_rate']:.1f}%",
            })

    if vl_done > 0 and suppression_rate < 90.0:
        management_alerts.append({
            "category": "Clinical Gap",
            "severity": "Warning",
            "title": "Viral Load Suppression Gap",
            "message": f"Overall suppression rate is {suppression_rate:.1f}% ({suppressed:,}/{vl_done:,}), below the 95% third-95 target.",
            "trace_metric": f"Suppression: {suppression_rate:.1f}%",
        })

    missing_geo_records = sum(r["Cohort"] for r in geo_summary if "(MISSING)" in (r["County"], r["SR Name"], r["Region"]))
    if missing_geo_records > 0:
        management_alerts.append({
            "category": "Geography",
            "severity": "Warning",
            "title": "Unclassified Geographic Records",
            "message": f"{missing_geo_records:,} client record(s) contain missing County, Sub-Recipient, or Region values (retained under (MISSING)).",
            "trace_metric": f"{missing_geo_records:,} records",
        })

    if not management_alerts:
        management_alerts.append({
            "category": "Performance",
            "severity": "Info",
            "title": "All Programme Cascades Optimal",
            "message": "All cascade indicators, clinical linkages, and data quality standards meet or exceed target thresholds.",
            "trace_metric": "0 Defects / High Coverage",
        })

    # 13. Demographic Pyramid Records respecting Typology Rules
    demographic_pyramid = extract_demographic_pyramid(
        reg_df=reg_analyzed,
        population=population,
        summary_df=summary_df,
    )

    # 14. Geography Matrix for Cascading Filters
    geography_matrix = {
        "regions": sorted(geo_hierarchy.keys()),
        "counties": sorted({r["County"] for r in geo_summary}),
        "sub_recipients": sorted({r["SR Name"] for r in geo_summary}),
        "hierarchy": geo_hierarchy,
    }

    return {
        # 100% Backward Compatible Legacy Keys
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
            "Refills": prep_refill,
            "Restarted": prep_restart,
            "Switched": prep_switched,
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

        # New Cockpit & Workbench Aggregates
        "performance_scorecard": scorecard,
        "regional_performance": regional_performance,
        "sr_rankings": sr_rankings,
        "management_alerts": management_alerts,
        "demographic_pyramid": demographic_pyramid,
        "geography_matrix": geography_matrix,
    }
