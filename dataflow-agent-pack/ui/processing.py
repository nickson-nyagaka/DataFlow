"""DATAFLOW Processing Page.

Orchestrates full pipeline execution with granular stage timings via st.status,
SHA-256 caching detection, and state machine transition to 'PROCESSED'.
Implements Decisions D-041 and Master Brief §11.
"""

from __future__ import annotations

import streamlit as st

from core.runner import compute_config_hash, get_cached_result, run_full_pipeline
from ui.session import render_access_guard


def render_processing() -> None:
    st.title("⚙️ Pipeline Processing")
    st.caption("Execute full automated ingestion, cleaning, data quality assurance, and reporting.")

    if not render_access_guard("Processing"):
        return

    file_bytes = st.session_state.get("uploaded_file_bytes")
    file_name = st.session_state.get("uploaded_file_name", "cohort_register.xlsx")
    file_hash = st.session_state.get("uploaded_file_hash", "")
    population = st.session_state.get("population", "FSW")
    period_mode = st.session_state.get("period_mode", "SEM")
    mask_ident = st.session_state.get("mask_identifiers", False)

    if not file_bytes:
        st.warning(
            "⚠️ No uploaded file found in memory. Please upload a file on the Upload page.", icon="⚠️"
        )
        return

    config_hash = compute_config_hash(population, period_mode)

    # Check for existing cache
    cached_result = get_cached_result(file_hash, config_hash, population, period_mode)

    # Overview of pending job
    with st.container():
        st.markdown("#### Job Specification")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Source File:** `{file_name}`")
        col2.markdown(f"**Target Population:** `{population}`")
        col3.markdown(f"**Reporting Period:** `{period_mode}`")

        col4, col5 = st.columns(2)
        col4.markdown(f"**File Hash (SHA-256):** `{file_hash[:20]}...`")
        col5.markdown(f"**Config Hash:** `{config_hash}`")

        st.divider()

    # Action buttons
    col_btn, col_force = st.columns([1, 1])
    start_run = False
    force_run = False

    with col_btn:
        start_label = (
            "⚡ Run Pipeline (Instant from Cache)"
            if cached_result
            else "🚀 Run Processing Pipeline"
        )
        if st.button(start_label, type="primary", use_container_width=True):
            start_run = True

    with col_force:
        if cached_result and st.button(
            "🔄 Force Fresh Execution (Bypass Cache)", use_container_width=True
        ):
            force_run = True

    if start_run or force_run:
        with st.status("Executing DATAFLOW analytical pipeline...", expanded=True) as status:
            try:
                st.write("📥 **Stage 1:** Ingesting register and KPLHIV worksheets...")
                st.write(
                    "🧹 **Stage 2:** Applying vectorized cleaning and missing geography standardization..."
                )
                st.write(
                    "🛡️ **Stage 3:** Evaluating 19 DQA rules across demographic and clinical fields..."
                )
                st.write(
                    "📈 **Stage 4:** Calculating 48 GF indicators, quarterly disaggregations, and KPLHIV metrics..."
                )
                st.write(
                    "📦 **Stage 5:** Assembling Master Multi-Tab Excel Workbook and Modular ZIP Package..."
                )

                # Execute pipeline through runner
                result = run_full_pipeline(
                    file_source=file_bytes,
                    file_name=file_name,
                    population=population,
                    period_mode=period_mode,
                    mask_identifiers=mask_ident,
                    force_rerun=force_run,
                )

                st.session_state["pipeline_result"] = result
                st.session_state["stage"] = "PROCESSED"
                st.session_state["stage_timings"] = result.stage_timings

                if result.cached:
                    status.update(
                        label=f"Pipeline Completed! (Retrieved from cache in {result.duration_seconds:.3f}s)",
                        state="complete",
                        expanded=False,
                    )
                else:
                    status.update(
                        label=f"Pipeline Completed Successfully in {result.duration_seconds:.2f}s!",
                        state="complete",
                        expanded=False,
                    )

            except Exception as exc:
                st.session_state["stage"] = "ERROR"
                st.session_state["error_message"] = str(exc)
                status.update(label="Pipeline Execution Failed", state="error", expanded=True)
                st.error(
                    f"❌ **Processing Error:** {exc}\n\n"
                    "Please check that the uploaded register follows the required template structure.",
                    icon="❌",
                )
                return

    # Render results if stage is PROCESSED
    if (
        st.session_state.get("stage") == "PROCESSED"
        and st.session_state.get("pipeline_result") is not None
    ):
        res = st.session_state["pipeline_result"]

        st.subheader("🎉 Processing Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cohort Clients", f"{res.total_cohort:,}")
        m2.metric("Active KPLHIV", f"{res.active_kplhiv:,}")
        m3.metric(
            "DQA Exceptions",
            f"{res.total_dqa_exceptions:,}",
            delta=f"{res.critical_dqa_count} Critical" if res.critical_dqa_count > 0 else "Clean",
            delta_color="inverse" if res.critical_dqa_count > 0 else "normal",
        )
        m4.metric("Execution Time", f"{res.duration_seconds:.2f}s")

        # Stage timing breakdown
        with st.expander("⏱️ Granular Stage Timings", expanded=False):
            t_cols = st.columns(len(res.stage_timings))
            for i, (stg, duration) in enumerate(res.stage_timings.items()):
                t_cols[i].metric(label=stg.title(), value=f"{duration:.3f}s")

        # Next step guidance
        st.markdown("#### Next Steps")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("🔍 Review Data Quality", use_container_width=True):
                st.session_state["active_page"] = "Data Quality"
                st.rerun()
        with b2:
            if st.button("📊 View Analytics", use_container_width=True):
                st.session_state["active_page"] = "Analytics"
                st.rerun()
        with b3:
            if st.button("📥 Download Reports", type="primary", use_container_width=True):
                st.session_state["active_page"] = "Export Reports"
                st.rerun()


render_processing()
