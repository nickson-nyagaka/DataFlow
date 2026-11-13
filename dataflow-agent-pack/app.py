"""DATAFLOW — Automated Key Population Data Management, Cleaning, Analytics & Reporting System.

Main application entrypoint.
Implements:
- Master Brief §3 (Sidebar Reorganization: 6 Workflow pages + 2 System pages).
- Master Brief §4 & §5 (Strict sequential workflow & centralized access gating).
- Master Brief §17 & §18 (Active Session overview, checklist, and New Session reset).
"""

from __future__ import annotations

import streamlit as st

from core.workflow_manager import WorkflowStage, get_workflow_checklist
from ui.session import get_current_workflow_stage, init_session_state, reset_session

st.set_page_config(
    page_title="DATAFLOW — Automated Reporting System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state machine
init_session_state()

# Define navigation structure strictly ordered per Master Brief §3
pages = {
    "Workflow": [
        st.Page("ui/upload.py", title="Upload Data", icon=":material/upload_file:", default=True),
        st.Page("ui/processing.py", title="Processing", icon=":material/sync:"),
        st.Page("ui/data_quality.py", title="Data Quality", icon=":material/fact_check:"),
        st.Page("ui/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
        st.Page("ui/analytics.py", title="Analytics", icon=":material/analytics:"),
        st.Page("ui/exports.py", title="Export Reports", icon=":material/download:"),
    ],
    "System": [
        st.Page("ui/configuration.py", title="Configuration", icon=":material/settings:"),
        st.Page("ui/about.py", title="About", icon=":material/info:"),
    ],
}

# Sidebar Session Controls & Branding per Master Brief §3 & §17
with st.sidebar:
    st.markdown("### 📊 DATAFLOW")
    st.caption("Automated Key Population Reporting")
    st.divider()

    st.markdown("#### 🧭 Active Session")
    current_stage = get_current_workflow_stage()
    pop = st.session_state.get("population", "FSW")
    per = st.session_state.get("period_mode", "SEM")
    fname = st.session_state.get("uploaded_file_name", "")
    has_active_session = current_stage != WorkflowStage.EMPTY or bool(fname)

    if not has_active_session:
        st.info("ℹ️ **NO ACTIVE SESSION**\n\nUpload a cohort register to begin.", icon="ℹ️")
    else:
        badge_color = {
            WorkflowStage.EMPTY: "gray",
            WorkflowStage.UPLOADED: "blue",
            WorkflowStage.PROCESSING: "orange",
            WorkflowStage.PROCESSED: "green",
            WorkflowStage.DQA_REVIEWED: "green",
            WorkflowStage.DASHBOARD_VIEWED: "green",
            WorkflowStage.ANALYTICS_VIEWED: "green",
            WorkflowStage.EXPORT_READY: "violet",
            WorkflowStage.COMPLETED: "rainbow",
        }.get(current_stage, "gray")

        st.markdown(f"**Status:** :{badge_color}[{current_stage.value.upper()}]")
        st.markdown(f"**Population:** `{pop}`")
        st.markdown(f"**Period:** `{per}`")

        if fname:
            short_name = f"{fname[:18]}..." if len(fname) > 18 else fname
            st.markdown(f"**File:** `{short_name}`")

        # Display progress percentage
        overall_pct = st.session_state.get("overall_progress", 0)
        if current_stage in (
            WorkflowStage.PROCESSED,
            WorkflowStage.DQA_REVIEWED,
            WorkflowStage.DASHBOARD_VIEWED,
            WorkflowStage.ANALYTICS_VIEWED,
            WorkflowStage.EXPORT_READY,
            WorkflowStage.COMPLETED,
        ):
            overall_pct = 100
        elif current_stage == WorkflowStage.EMPTY:
            overall_pct = 0
        st.markdown(f"**Progress:** `{int(overall_pct)}%`")

        st.markdown("---")
        st.markdown("**Workflow Stage:**")
        checklist = get_workflow_checklist(current_stage)
        for item in checklist:
            icon = item["icon"]
            title = item["title"]
            if icon == "✓":
                st.markdown(f"&nbsp;&nbsp;`{icon}` **{title}**")
            elif icon == "●":
                st.markdown(f"&nbsp;&nbsp;:{badge_color}[`{icon}` **{title}**]")
            else:
                st.markdown(f"&nbsp;&nbsp;`{icon}` <span style='color:gray'>{title}</span>", unsafe_allow_html=True)

    st.divider()

    # Master Brief §18: New Session complete workflow reset
    if st.button(
        "🔄 New Session",
        use_container_width=True,
        type="secondary",
        help="Invalidates current session, purges memory & temporary files, and resets workflow to Upload Data.",
    ):
        reset_session()
        st.rerun()

    st.divider()
    st.caption("🔒 Kenya KP Data Standard\nLocalhost 127.0.0.1 Binding")

# Run navigation
pg = st.navigation(pages)
pg.run()
