"""DATAFLOW Dashboard Page.

Displays executive metrics, programmatic cascades, and execution status from
pre-calculated presentation analytics and run metadata.

Implements Master Brief §11 and Decisions D-040/D-041:
- Zero analytical calculations, groupby, or formulas on this page (pure presentation).
- All primary metric cards trace directly to runtime/run_metadata.json (zero hardcoded numbers).
- Visual cascade charts and distribution graphs reflect the actual statistics of the uploaded dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root takes precedence over ui/ in sys.path to prevent module collision with ui/analytics.py
_ROOT = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] != _ROOT:
    if _ROOT in sys.path:
        sys.path.remove(_ROOT)
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from core.workflow_manager import WorkflowStage  # noqa: E402
from ui.session import advance_workflow_stage, render_access_guard  # noqa: E402


def render_dashboard() -> None:
    st.title("📊 Cohort Performance Dashboard")
    st.caption(
        "Executive overview of cohort ingestion, quality assurance, and key population metrics."
    )

    if not render_access_guard("Dashboard"):
        return

    # 1. Retrieve session pipeline result (active session strictly prioritized per §12.1)
    res = st.session_state.get("pipeline_result")
    if not res:
        st.warning("No active processed pipeline result found in this session.")
        return

    # Record dashboard viewed in session
    st.session_state["dashboard_viewed"] = True

    total_cohort = res.total_cohort
    active_kplhiv = res.active_kplhiv
    total_dqa = res.total_dqa_exceptions
    duration = res.duration_seconds
    crit_count = res.critical_dqa_count
    major_count = res.major_dqa_count
    minor_count = res.minor_dqa_count
    population = res.population
    period_mode = res.period_mode
    file_name = res.input_file_name
    file_hash = res.input_file_hash
    ts = res.timestamp
    timings = res.stage_timings
    disp = res.display_analytics

    # Metric Cards (Guaranteed identical structure and labels for exit criteria compliance)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Total Cohort Clients",
        value=f"{total_cohort:,}",
        help="Total deduplicated client records in the registered cohort.",
    )
    col2.metric(
        label="Active KPLHIV",
        value=f"{active_kplhiv:,}",
        help="Clients active on ART in the KPLHIV tracking sheet.",
    )
    col3.metric(
        label="DQA Exceptions",
        value=f"{total_dqa:,}",
        delta=f"{crit_count} Critical" if crit_count > 0 else "0 Critical",
        delta_color="inverse" if crit_count > 0 else "normal",
        help="Quality assurance exceptions found across all rules.",
    )
    col4.metric(
        label="Pipeline Duration",
        value=f"{duration:.2f}s",
        help="Total wall-clock duration of the last pipeline run.",
    )

    # 2. Programme Executive Performance Cards (when display analytics available)
    exec_kpis = disp.get("executive_metrics", {})
    if exec_kpis:
        st.divider()
        st.subheader(f"🎯 Executive Performance Indicators — {population} ({period_mode})")
        k1, k2, k3, k4 = st.columns(4)

        dp_count = exec_kpis.get("defined_package", 0)
        dp_rate = exec_kpis.get("defined_package_rate", 0.0)
        tested_count = exec_kpis.get("hts_tested", 0)
        tested_rate = exec_kpis.get("testing_rate", 0.0)
        prep_count = exec_kpis.get("prep_active", 0)
        supp_count = exec_kpis.get("virally_suppressed", 0)
        supp_rate = exec_kpis.get("suppression_rate", 0.0)

        k1.metric(
            label="Defined Package Reached",
            value=f"{dp_count:,}",
            delta=f"{dp_rate}% Cohort",
            help="Clients receiving standard Global Fund defined prevention package.",
        )
        k2.metric(
            label="HTS Clients Tested",
            value=f"{tested_count:,}",
            delta=f"{tested_rate}% Reached",
            help="Total registered clients tested for HIV in the reporting period.",
        )
        k3.metric(
            label="Active on PrEP",
            value=f"{prep_count:,}",
            help="Total key population clients actively receiving PrEP medications.",
        )
        k4.metric(
            label="Virally Suppressed",
            value=f"{supp_count:,}",
            delta=f"{supp_rate}% VL Done",
            delta_color="normal",
            help="KPLHIV clients with documented viral load suppression (<1,000 cp/ml).",
        )

    # 3. Programme Cascade Visualizations (Bar Graphs)
    if disp:
        st.divider()
        st.subheader("📈 Core Programme Cascades")

        # Row 1: HTS Cascade & 95-95-95 Clinical Cascade
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### 🔬 HIV Testing Services (HTS) Cascade")
            hts_data = disp.get("hts_cascade", {})
            if hts_data:
                hts_df = pd.DataFrame(
                    {"Cascade Stage": list(hts_data.keys()), "Clients": list(hts_data.values())}
                ).set_index("Cascade Stage")
                st.bar_chart(hts_df, color="#e81349")
            else:
                st.caption("No HTS cascade data available.")

        with chart_col2:
            st.markdown("##### 💊 95-95-95 Care & Treatment Cascade")
            art_data = disp.get("art_cascade", {})
            if art_data:
                art_df = pd.DataFrame(
                    {"ART Stage": list(art_data.keys()), "Count": list(art_data.values())}
                ).set_index("ART Stage")
                st.bar_chart(art_df, color="#2ca02c")
            else:
                st.caption("No ART cascade data available.")

        # Row 2: Clinical Screening & Age Demographics
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.markdown("##### 🩺 Clinical Screening & Management (STI / TB)")
            clin_data = disp.get("clinical_cascade", {})
            if clin_data:
                clin_df = pd.DataFrame(
                    {"Service": list(clin_data.keys()), "Clients": list(clin_data.values())}
                ).set_index("Service")
                st.bar_chart(clin_df, color="#ff7f0e")
            else:
                st.caption("No clinical screening data available.")

        with chart_col4:
            st.markdown("##### 👥 Cohort Age Group Distribution")
            demo_data = disp.get("demographics", {})
            if demo_data:
                demo_df = pd.DataFrame(
                    {"Age Group": list(demo_data.keys()), "Clients": list(demo_data.values())}
                ).set_index("Age Group")
                st.bar_chart(demo_df, color="#6c00d2")
            else:
                st.caption("No demographic data available.")

        # Row 3: Commodity Distribution & Harm Reduction
        comm_data = disp.get("commodities", {})
        if comm_data:
            st.divider()
            st.subheader("📦 Commodity Distribution & Prevention Reached")
            comm_cols = st.columns(len(comm_data))
            for i, (comm_name, val) in enumerate(comm_data.items()):
                comm_cols[i].metric(label=comm_name, value=f"{val:,}")

            comm_df = pd.DataFrame(
                {"Commodity": list(comm_data.keys()), "Total Units": list(comm_data.values())}
            ).set_index("Commodity")
            st.bar_chart(comm_df, color="#00cee5")

    # 2. Programme Executive Performance Cards (when display analytics available)
    exec_kpis = disp.get("executive_metrics", {})
    if exec_kpis:
        st.divider()
        st.subheader(f"🎯 Executive Performance Indicators — {population} ({period_mode})")
        k1, k2, k3, k4 = st.columns(4)

        dp_count = exec_kpis.get("defined_package", 0)
        dp_rate = exec_kpis.get("defined_package_rate", 0.0)
        tested_count = exec_kpis.get("hts_tested", 0)
        tested_rate = exec_kpis.get("testing_rate", 0.0)
        prep_count = exec_kpis.get("prep_active", 0)
        supp_count = exec_kpis.get("virally_suppressed", 0)
        supp_rate = exec_kpis.get("suppression_rate", 0.0)

        k1.metric(
            label="Defined Package Reached",
            value=f"{dp_count:,}",
            delta=f"{dp_rate}% Cohort",
            help="Clients receiving standard Global Fund defined prevention package.",
        )
        k2.metric(
            label="HTS Clients Tested",
            value=f"{tested_count:,}",
            delta=f"{tested_rate}% Reached",
            help="Total registered clients tested for HIV in the reporting period.",
        )
        k3.metric(
            label="Active on PrEP",
            value=f"{prep_count:,}",
            help="Total key population clients actively receiving PrEP medications.",
        )
        k4.metric(
            label="Virally Suppressed",
            value=f"{supp_count:,}",
            delta=f"{supp_rate}% VL Done",
            delta_color="normal",
            help="KPLHIV clients with documented viral load suppression (<1,000 cp/ml).",
        )

    # 3. Programme Cascade Visualizations (Bar Graphs)
    if disp:
        st.divider()
        st.subheader("📈 Core Programme Cascades")

        # Row 1: HTS Cascade & 95-95-95 Clinical Cascade
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### 🔬 HIV Testing Services (HTS) Cascade")
            hts_data = disp.get("hts_cascade", {})
            if hts_data:
                hts_df = pd.DataFrame(
                    {"Cascade Stage": list(hts_data.keys()), "Clients": list(hts_data.values())}
                ).set_index("Cascade Stage")
                st.bar_chart(hts_df, color="#1f77b4")
            else:
                st.caption("No HTS cascade data available.")

        with chart_col2:
            st.markdown("##### 💊 95-95-95 Care & Treatment Cascade")
            art_data = disp.get("art_cascade", {})
            if art_data:
                art_df = pd.DataFrame(
                    {"ART Stage": list(art_data.keys()), "Count": list(art_data.values())}
                ).set_index("ART Stage")
                st.bar_chart(art_df, color="#2ca02c")
            else:
                st.caption("No ART cascade data available.")

        # Row 2: Clinical Screening & Age Demographics
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.markdown("##### 🩺 Clinical Screening & Management (STI / TB)")
            clin_data = disp.get("clinical_cascade", {})
            if clin_data:
                clin_df = pd.DataFrame(
                    {"Service": list(clin_data.keys()), "Clients": list(clin_data.values())}
                ).set_index("Service")
                st.bar_chart(clin_df, color="#ff7f0e")
            else:
                st.caption("No clinical screening data available.")

        with chart_col4:
            st.markdown("##### 👥 Cohort Age Group Distribution")
            demo_data = disp.get("demographics", {})
            if demo_data:
                demo_df = pd.DataFrame(
                    {"Age Group": list(demo_data.keys()), "Clients": list(demo_data.values())}
                ).set_index("Age Group")
                st.bar_chart(demo_df, color="#9467bd")
            else:
                st.caption("No demographic data available.")

        # Row 3: Commodity Distribution & Harm Reduction
        comm_data = disp.get("commodities", {})
        if comm_data:
            st.divider()
            st.subheader("📦 Commodity Distribution & Prevention Reached")
            comm_cols = st.columns(len(comm_data))
            for i, (comm_name, val) in enumerate(comm_data.items()):
                comm_cols[i].metric(label=comm_name, value=f"{val:,}")

            comm_df = pd.DataFrame(
                {"Commodity": list(comm_data.keys()), "Total Units": list(comm_data.values())}
            ).set_index("Commodity")
            st.bar_chart(comm_df, color="#17becf")

    st.divider()

    # 4. DQA Health Banner
    if crit_count > 0:
        st.warning(
            f"⚠️ **Data Quality Alert:** {crit_count} Critical exception(s) detected "
            f"({major_count} Major, {minor_count} Minor). "
            "Report exports remain accessible, but source records should be verified.",
            icon="⚠️",
        )
    else:
        st.success(
            f"✅ **Clean Pipeline Status:** 0 Critical DQA exceptions detected "
            f"({major_count} Major, {minor_count} Minor). All reporting packages are ready for export.",
            icon="✅",
        )

    # 5. Run Metadata & Timing Details
    with st.expander("📋 Latest Run Metadata & Stage Timings", expanded=False):
        col_meta, col_time = st.columns([1, 1])

        with col_meta:
            st.markdown("#### Execution Information")
            st.write(f"**Target Population:** `{population}`")
            st.write(f"**Reporting Period:** `{period_mode}`")
            st.write(f"**Source File:** `{file_name}`")
            st.write(
                f"**File Hash (SHA-256):** `{file_hash[:16]}...`"
                if len(file_hash) > 16
                else f"`{file_hash}`"
            )
            st.write(f"**Timestamp (UTC):** `{ts}`")

        with col_time:
            st.markdown("#### Stage Timings")
            if timings:
                for stage, sec in timings.items():
                    st.write(f"• **{stage.title()}:** `{sec:.3f}s`")
            else:
                st.write("No granular timings recorded.")

    # 6. Workflow Progression: Continue to Analytics per Master Brief §12
    st.divider()
    st.subheader("🏁 Next Workflow Step")
    st.caption("Proceed to deep-dive analytics and indicator disaggregations.")

    col_inf, col_btn = st.columns([2, 1])
    with col_inf:
        st.info("ℹ️ Proceed to inspect cascade breakdowns and facility-level summaries.")
    with col_btn:
        if st.button("📈 Proceed to Analytics ➡️", type="primary", use_container_width=True):
            advance_workflow_stage(WorkflowStage.DASHBOARD_VIEWED)
            st.switch_page("ui/analytics.py")


render_dashboard()
