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
    st.caption("Pre-aggregated cascade metrics and commodity distribution summaries.")

    if not render_access_guard("Analytics"):
        return

    result = st.session_state.get("pipeline_result")
    if not result:
        st.warning("No pipeline results available. Please run processing first.")
        return

    disp = result.display_analytics
    population = result.population
    period_mode = result.period_mode

    st.subheader(f"1. HIV Testing Services (HTS) Cascade — {population} ({period_mode})")
    hts_data = disp.get("hts_cascade", {})

    col1, col2, col3, col4 = st.columns(4)
    tested = hts_data.get("Tested", 0)
    neg = hts_data.get("Negative", 0)
    pos = hts_data.get("Positive", 0)
    linked = hts_data.get("Linked", 0)

    col1.metric("Clients Tested", f"{tested:,}")
    col2.metric("Negative", f"{neg:,}")
    col3.metric("Positive", f"{pos:,}")
    col4.metric("Linked to ART", f"{linked:,}")

    # Display bar chart from pre-calculated dictionary
    hts_df = pd.DataFrame(
        {
            "Cascade Stage": list(hts_data.keys()),
            "Clients": list(hts_data.values()),
        }
    ).set_index("Cascade Stage")
    st.bar_chart(hts_df)

    st.divider()

    st.subheader(f"2. Pre-Exposure Prophylaxis (PrEP) Cascade — {population}")
    prep_data = disp.get("prep_cascade", {})

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Screened", f"{prep_data.get('Screened', 0):,}")
    p2.metric("Eligible", f"{prep_data.get('Eligible', 0):,}")
    p3.metric("Initiated (New)", f"{prep_data.get('Initiated', 0):,}")
    p4.metric("Refills", f"{prep_data.get('Refills', 0):,}")
    p5.metric("Discontinued", f"{prep_data.get('Discontinued', 0):,}")

    prep_df = pd.DataFrame(
        {
            "PrEP Indicator": list(prep_data.keys()),
            "Clients": list(prep_data.values()),
        }
    ).set_index("PrEP Indicator")
    st.bar_chart(prep_df)

    st.divider()

    st.subheader(f"3. Antiretroviral Therapy (ART) & Viral Suppression — {population}")
    art_data = disp.get("art_cascade", {})

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Active KPLHIV", f"{art_data.get('Active KPLHIV', 0):,}")
    a2.metric("On ART", f"{art_data.get('On ART', 0):,}")
    a3.metric("Viral Load Done", f"{art_data.get('Viral Load Done', 0):,}")
    a4.metric("Suppressed (<1000 cp/ml)", f"{art_data.get('Suppressed', 0):,}")

    art_df = pd.DataFrame(
        {
            "ART Stage": list(art_data.keys()),
            "Count": list(art_data.values()),
        }
    ).set_index("ART Stage")
    st.bar_chart(art_df)

    st.divider()

    st.subheader(f"4. Commodities Distribution — {population}")
    comm_data = disp.get("commodities", {})

    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.metric("Male Condoms", f"{comm_data.get('Male Condoms', 0):,}")
    cm2.metric("Female Condoms", f"{comm_data.get('Female Condoms', 0):,}")
    cm3.metric("Lubricants", f"{comm_data.get('Lubricants', 0):,}")
    if population == "PWID":
        cm4.metric("Needles & Syringes", f"{comm_data.get('Needles & Syringes', 0):,}")
    else:
        cm4.metric("Needles & Syringes", "N/A (PWID only)")

    comm_df = pd.DataFrame(
        {
            "Commodity": list(comm_data.keys()),
            "Units Distributed": list(comm_data.values()),
        }
    ).set_index("Commodity")
    st.bar_chart(comm_df)

    st.divider()

    # Facility & County Summary Table (Render pre-built summary_df directly)
    st.subheader("5. Geographic Indicator Summary Table")
    st.caption(
        "Standardized summary aggregated by County, Sub-Recipient, and Region with (MISSING) retention."
    )
    if result.summary_df is not None and not result.summary_df.empty:
        st.dataframe(result.summary_df, use_container_width=True, hide_index=True)


render_analytics()
