"""DATAFLOW Dashboard Page.

Displays executive metrics and execution status from the latest run metadata JSON.
Implements Master Brief §11:
- All figures trace directly to runtime/run_metadata.json (zero hardcoded numbers).
- Zero indicator formula calculations on this page.
"""

from __future__ import annotations

import streamlit as st

from core.runner import read_latest_run_metadata


def render_dashboard() -> None:
    st.title("📊 Cohort Performance Dashboard")
    st.caption(
        "Executive overview of latest cohort ingestion, quality assurance, and key population metrics."
    )

    meta = read_latest_run_metadata()

    if not meta:
        st.info(
            "ℹ️ **No pipeline runs recorded yet.** "
            "Navigate to **Upload Data** in the sidebar to upload and process a Key Population cohort register.",
            icon="ℹ️",
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="Total Cohort", value="—")
        col2.metric(label="Active KPLHIV", value="—")
        col3.metric(label="DQA Exceptions", value="—")
        col4.metric(label="Run Duration", value="—")
        return

    # Extract metrics from run metadata
    total_cohort = meta.get("total_cohort", 0)
    active_kplhiv = meta.get("active_kplhiv", 0)
    total_dqa = meta.get("total_dqa_exceptions", 0)
    duration = meta.get("duration_seconds", 0.0)
    crit_count = meta.get("critical_dqa_count", 0)
    major_count = meta.get("major_dqa_count", 0)
    minor_count = meta.get("minor_dqa_count", 0)
    population = meta.get("population", "N/A")
    period_mode = meta.get("period_mode", "N/A")
    file_name = meta.get("input_file_name", "N/A")
    file_hash = meta.get("input_file_hash", "N/A")
    ts = meta.get("timestamp", "N/A")

    # Metric Cards
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

    st.divider()

    # DQA Health Banner
    if crit_count > 0:
        st.warning(
            f"⚠️ **Data Quality Alert:** {crit_count} Critical exception(s) detected "
            f"({major_count} Major, {minor_count} Minor). "
            "Report exports may be gated until source records are corrected or authorized overrides are applied.",
            icon="⚠️",
        )
    else:
        st.success(
            f"✅ **Clean Pipeline Status:** 0 Critical DQA exceptions detected. "
            f"({major_count} Major, {minor_count} Minor). All reporting packages are ready for export.",
            icon="✅",
        )

    # Run Metadata & Timing Details
    with st.expander("📋 Latest Run Metadata & Stage Timings", expanded=True):
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
            timings = meta.get("stage_timings", {})
            if timings:
                for stage, sec in timings.items():
                    st.write(f"• **{stage.title()}:** `{sec:.3f}s`")
            else:
                st.write("No granular timings recorded.")


render_dashboard()
