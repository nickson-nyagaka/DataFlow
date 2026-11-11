"""DATAFLOW — Automated Key Population Data Management, Cleaning, Analytics & Reporting System.

Main application entrypoint.
Implements:
- Decision D-040 (Modern st.navigation with Workflow, Inspection, System groupings).
- Decision D-041 (Guided state machine integration).
- Decision D-044 (New Session cleanup action).
"""

from __future__ import annotations

import streamlit as st

from ui.session import init_session_state, reset_session

st.set_page_config(
    page_title="DATAFLOW — Automated Reporting System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state machine
init_session_state()

# Define navigation structure per Decision D-040
pages = {
    "Workflow": [
        st.Page("ui/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("ui/upload.py", title="Upload Data", icon=":material/upload_file:"),
        st.Page("ui/processing.py", title="Processing", icon=":material/sync:"),
        st.Page("ui/exports.py", title="Export Reports", icon=":material/download:"),
    ],
    "Inspection": [
        st.Page("ui/data_quality.py", title="Data Quality", icon=":material/fact_check:"),
        st.Page("ui/analytics.py", title="Analytics", icon=":material/analytics:"),
    ],
    "System": [
        st.Page("ui/configuration.py", title="Configuration", icon=":material/settings:"),
        st.Page("ui/about.py", title="About", icon=":material/info:"),
    ],
}

# Sidebar Session Controls & Branding
with st.sidebar:
    st.markdown("### 📊 DATAFLOW")
    st.caption("Automated Key Population Reporting")
    st.divider()

    st.markdown("#### Active Session")
    stage = st.session_state.get("stage", "IDLE")
    pop = st.session_state.get("population", "FSW")
    per = st.session_state.get("period_mode", "SEM")

    badge_color = {
        "IDLE": "gray",
        "UPLOADED": "blue",
        "PROCESSING": "orange",
        "PROCESSED": "green",
        "ERROR": "red",
    }.get(stage, "gray")

    st.markdown(f"• **Status:** :{badge_color}[{stage}]")
    st.markdown(f"• **Population:** `{pop}`")
    st.markdown(f"• **Period:** `{per}`")

    if st.session_state.get("uploaded_file_name"):
        fname = st.session_state["uploaded_file_name"]
        st.markdown(
            f"• **File:** `{fname[:18]}...`" if len(fname) > 18 else f"• **File:** `{fname}`"
        )

    st.divider()

    # Decision D-044: New Session purges memory and runtime/temporary/
    if st.button(
        "🔄 New Session",
        use_container_width=True,
        help="Purges session state and deletes temporary files.",
    ):
        reset_session()
        st.rerun()

    st.divider()
    st.caption("🔒 Kenya KP Data Standard\nLocalhost 127.0.0.1 Binding")

# Run navigation
pg = st.navigation(pages)
pg.run()
