"""DATAFLOW Analytics Presentation Page.

Implements Master Brief §11 and Phase Plan exit criteria:
- Pure presentation layer: displays charts and metrics reading ONLY pre-calculated summaries.
- STRICT CONSTRAINT: Zero indicator logic, formulas, or groupby/agg in ui/.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.session import render_access_guard


def render_analytics() -> None:
    st.title("📊 Key Population Analytics")
    st.caption("Pre-aggregated cascade metrics, clinical services, and commodity distribution summaries.")

    if not render_access_guard("Analytics"):
        return

    result = st.session_state.get("pipeline_result")
    if not result:
        st.warning("No pipeline results available. Please run processing first.")
        return

    disp = result.display_analytics
    population = result.population
    period_mode = result.period_mode

    # 1. HTS Cascade
    st.subheader(f"1. HIV Testing Services (HTS) Cascade — {population} ({period_mode})")
    hts_data = disp.get("hts_cascade", {})

    col1, col2, col3, col4 = st.columns(4)
    tested = hts_data.get("Tested", 0)
    neg = hts_data.get("Negative", 0)
    pos = hts_data.get("Positive", 0)
    linked = hts_data.get("Linked to ART", hts_data.get("Linked", 0))

    col1.metric("Clients Tested", f"{tested:,}")
    col2.metric("Negative", f"{neg:,}")
    col3.metric("Positive", f"{pos:,}")
    col4.metric("Linked to ART", f"{linked:,}")

    if hts_data:
        hts_df = pd.DataFrame(
            {
                "Cascade Stage": list(hts_data.keys()),
                "Clients": list(hts_data.values()),
            }
        ).set_index("Cascade Stage")
        st.bar_chart(hts_df, color="#1f77b4")

    st.divider()

    # 2. PrEP Cascade
    st.subheader(f"2. Pre-Exposure Prophylaxis (PrEP) Cascade — {population}")
    prep_data = disp.get("prep_cascade", {})

    p1, p2, p3, p4 = st.columns(4)
    p_act = prep_data.get("Active on PrEP", prep_data.get("Screened", 0))
    p_init = prep_data.get("Initiated (New)", prep_data.get("Initiated", 0))
    p_ref = prep_data.get("Refills / Continuing", prep_data.get("Refills", 0))
    p_disc = prep_data.get("Discontinued", 0)

    p1.metric("Active on PrEP", f"{p_act:,}")
    p2.metric("Initiated (New)", f"{p_init:,}")
    p3.metric("Refills / Continuing", f"{p_ref:,}")
    p4.metric("Discontinued", f"{p_disc:,}")

    if prep_data:
        prep_df = pd.DataFrame(
            {
                "PrEP Indicator": list(prep_data.keys()),
                "Clients": list(prep_data.values()),
            }
        ).set_index("PrEP Indicator")
        st.bar_chart(prep_df, color="#2ca02c")

    st.divider()

    # 3. ART & Viral Suppression
    st.subheader(f"3. Antiretroviral Therapy (ART) & Viral Suppression — {population}")
    art_data = disp.get("art_cascade", {})

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Active KPLHIV", f"{art_data.get('Active KPLHIV', 0):,}")
    a2.metric("On ART", f"{art_data.get('On ART', 0):,}")
    a3.metric("Viral Load Done", f"{art_data.get('Viral Load Done', 0):,}")
    a4.metric("Suppressed (<1000 cp/ml)", f"{art_data.get('Suppressed (<1000 cp/ml)', art_data.get('Suppressed', 0)):,}")

    if art_data:
        art_df = pd.DataFrame(
            {
                "ART Stage": list(art_data.keys()),
                "Count": list(art_data.values()),
            }
        ).set_index("ART Stage")
        st.bar_chart(art_df, color="#d62728")

    st.divider()

    # 4. Clinical Services (STI & TB)
    st.subheader(f"4. Clinical Screening & Management (STI / TB) — {population}")
    clin_data = disp.get("clinical_cascade", {})

    cl1, cl2, cl3, cl4 = st.columns(4)
    cl1.metric("STI Screened", f"{clin_data.get('STI Screened', 0):,}")
    cl2.metric("STI Diagnosed", f"{clin_data.get('STI Diagnosed', 0):,}")
    cl3.metric("STI Treated", f"{clin_data.get('STI Treated', 0):,}")
    cl4.metric("TB Screened", f"{clin_data.get('TB Screened', 0):,}")

    if clin_data:
        clin_df = pd.DataFrame(
            {
                "Clinical Service": list(clin_data.keys()),
                "Clients": list(clin_data.values()),
            }
        ).set_index("Clinical Service")
        st.bar_chart(clin_df, color="#ff7f0e")

    st.divider()

    # 5. Commodities Distribution
    st.subheader(f"5. Commodities Distribution & Prevention Reached — {population}")
    comm_data = disp.get("commodities", {})

    if comm_data:
        comm_cols = st.columns(len(comm_data))
        for idx, (label, val) in enumerate(comm_data.items()):
            comm_cols[idx].metric(label, f"{val:,}")

        comm_df = pd.DataFrame(
            {
                "Commodity": list(comm_data.keys()),
                "Units / Contacts": list(comm_data.values()),
            }
        ).set_index("Commodity")
        st.bar_chart(comm_df, color="#17becf")

    st.divider()

    # 6. Demographics Age Distribution
    st.subheader(f"6. Demographic Age Group Distribution — {population}")
    demo_data = disp.get("demographics", {})
    if demo_data:
        dm1, dm2, dm3, dm4 = st.columns(4)
        dm1.metric("Below 15", f"{demo_data.get('Below 15', 0):,}")
        dm2.metric("15–19", f"{demo_data.get('15–19', 0):,}")
        dm3.metric("20–24", f"{demo_data.get('20–24', 0):,}")
        dm4.metric("25+", f"{demo_data.get('25+', 0):,}")

        demo_df = pd.DataFrame(
            {
                "Age Group": list(demo_data.keys()),
                "Clients": list(demo_data.values()),
            }
        ).set_index("Age Group")
        st.bar_chart(demo_df, color="#9467bd")

    st.divider()

    # 7. Facility & County Summary Table (Render pre-built summary_df directly)
    st.subheader("7. Geographic Indicator Summary Table")
    st.caption(
        "Standardized summary aggregated by County, Sub-Recipient, and Region with (MISSING) retention."
    )
    if result.summary_df is not None and not result.summary_df.empty:
        st.dataframe(result.summary_df, use_container_width=True, hide_index=True)

    # 8. KPI Indicators by Age and Sex Table
    kpi_df = disp.get("kpi_summary_df")
    if kpi_df is not None and not kpi_df.empty:
        st.divider()
        st.subheader("8. KPI Indicators by Age and Sex")
        st.caption("Key Programme Indicators (Defined Package, HTS, PrEP) disaggregated by demographic categories (notebook Cell 84).")
        st.dataframe(kpi_df, use_container_width=True, hide_index=True)


render_analytics()
