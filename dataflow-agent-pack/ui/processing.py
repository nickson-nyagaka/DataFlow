"""DATAFLOW Processing Page.

Implements Master Brief §7, §8, §9, §10:
- Real-time individual progress ribbons for all five analytical stages.
- Mathematically normalized overall pipeline progress ribbon.
- Event-driven non-simulated execution monitoring.
- Strict workflow gating: transitions to PROCESSED and unlocks Data Quality only.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.runner import compute_config_hash, get_cached_result, run_full_pipeline
from core.workflow_manager import WorkflowStage
from ui.session import advance_workflow_stage, render_access_guard


def render_processing() -> None:
    st.title("⚙️ Automated Pipeline Processing")
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

    # 1. Overview of pending job
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

    # 2. Action buttons
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

    # Containers for live progress ribbons per Master Brief §8
    st.markdown("### 📊 Pipeline Execution Progress")
    overall_container = st.container()
    stages_container = st.container()

    # Define clean stage UI metadata
    stage_meta = [
        ("ingestion", "📥 Stage 1: Workbook Ingestion", "Ingesting register & KPLHIV sheets"),
        ("cleaning", "🧹 Stage 2: Data Cleaning & Normalization", "Vectorized cleaning & geography"),
        ("dqa", "🛡️ Stage 3: Data Quality Assessment (DQA)", "Evaluating clinical & demographic DQA rules"),
        ("analytics", "📈 Stage 4: Analytical Calculations", "Calculating cascade indicators & summaries"),
        ("reporting", "📦 Stage 5: Reporting Package Assembly", "Assembling Master workbook & ZIP package"),
    ]

    prior_result = st.session_state.get("pipeline_result")

    # Initialize live placeholders
    with overall_container:
        st.markdown("#### Overall Pipeline Progress")
        overall_progress_bar = st.progress(1.0 if prior_result else 0.0)
        overall_status_text = st.empty()
        if prior_result:
            total_m = prior_result.duration_seconds / 60.0
            overall_status_text.markdown(f"**Progress:** `100% COMPLETED` ✅ • Total Time: **{total_m:.2f} min** ({prior_result.duration_seconds:.2f}s)")
        else:
            overall_status_text.markdown("**Progress:** `0% PENDING`")

    stage_placeholders: dict[str, dict[str, Any]] = {}
    with stages_container:
        for s_id, title, desc in stage_meta:
            exp = st.container()
            with exp:
                header_slot = st.empty()
                pbar_slot = st.progress(1.0 if prior_result else 0.0)
                details_slot = st.empty()

                if prior_result:
                    dur_s = prior_result.stage_timings.get(s_id, 0.0)
                    dur_m = dur_s / 60.0
                    header_slot.markdown(f"**{title}** — :green[COMPLETED] (`100%`) • ⏱️ **{dur_m:.2f} min** ({dur_s:.2f}s)")
                    details_slot.caption(f"✓ Execution completed in {dur_m:.2f} minutes ({dur_s:.2f} seconds)")
                else:
                    header_slot.markdown(f"**{title}** — `:gray[PENDING]`")
                    details_slot.caption(f"Waiting to execute: {desc}")

                st.markdown("---")
                stage_placeholders[s_id] = {
                    "header": header_slot,
                    "bar": pbar_slot,
                    "details": details_slot,
                    "title": title,
                }

    if start_run or force_run:
        advance_workflow_stage(WorkflowStage.PROCESSING)

        def on_pipeline_progress(snapshot: dict[str, Any]) -> None:
            ov_pct = snapshot.get("overall_progress", 0.0)
            overall_progress_bar.progress(ov_pct / 100.0)
            overall_status_text.markdown(f"**Progress:** `{int(ov_pct)}% COMPLETED`")

            for s_id, s_data in snapshot.get("stages", {}).items():
                if s_id in stage_placeholders:
                    p = stage_placeholders[s_id]
                    status = s_data["status"].upper()
                    pct = s_data["progress_pct"] / 100.0
                    p["bar"].progress(pct)

                    color = "green" if status == "COMPLETED" else "orange" if status == "RUNNING" else "red" if status == "FAILED" else "gray"
                    dur_s = s_data.get("duration_seconds", 0.0)
                    dur_m = s_data.get("duration_minutes", dur_s / 60.0)
                    time_badge = f" • ⏱️ **{dur_m:.2f} min** ({dur_s:.1f}s)" if dur_s > 0 else ""
                    p["header"].markdown(f"**{p['title']}** — :{color}[{status}] (`{int(s_data['progress_pct'])}%`){time_badge}")

                    detail_text = f"• **Current Operation:** {s_data['current_operation']}"
                    if s_data.get("completed_operations"):
                        ops = " ".join([f"`✓ {op}`" for op in s_data["completed_operations"]])
                        detail_text += f"\n\n• **Completed:** {ops}"
                    p["details"].markdown(detail_text)

        try:
            result = run_full_pipeline(
                file_source=file_bytes,
                file_name=file_name,
                population=population,
                period_mode=period_mode,
                mask_identifiers=mask_ident,
                force_rerun=force_run,
                progress_callback=on_pipeline_progress,
            )

            # Store result and advance state
            st.session_state["pipeline_result"] = result
            st.session_state["stage_timings"] = result.stage_timings
            st.session_state["overall_progress"] = 100.0
            advance_workflow_stage(WorkflowStage.PROCESSED)

            # Ensure all UI bars display 100% on completion with stage times in minutes
            overall_progress_bar.progress(1.0)
            total_mins = result.duration_seconds / 60.0
            overall_status_text.markdown(f"**Progress:** `100% COMPLETED` ✅ • Total Time: **{total_mins:.2f} min** ({result.duration_seconds:.2f}s)")
            for s_id, p in stage_placeholders.items():
                dur_s = result.stage_timings.get(s_id, 0.0)
                dur_m = dur_s / 60.0
                p["bar"].progress(1.0)
                p["header"].markdown(f"**{p['title']}** — :green[COMPLETED] (`100%`) • ⏱️ **{dur_m:.2f} min** ({dur_s:.2f}s)")

            st.success(
                f"✅ **Pipeline Completed Successfully!** Processed in **{total_mins:.2f} min** ({result.duration_seconds:.2f}s) "
                f"{'(Retrieved from cache)' if result.cached else ''}.",
                icon="✅",
            )

        except Exception as exc:
            st.session_state["stage"] = "ERROR"
            st.session_state["error_message"] = str(exc)
            st.error(
                f"❌ **Processing Error:** {exc}\n\n"
                "Downstream stages have been halted. Please verify that the uploaded register follows the required template structure.",
                icon="❌",
            )
            return

    # 3. Render results and guided transition if stage is PROCESSED or further
    current_stage = st.session_state.get("workflow_stage", WorkflowStage.EMPTY)
    result = st.session_state.get("pipeline_result")

    if result is not None and current_stage not in (WorkflowStage.EMPTY, WorkflowStage.UPLOADED, WorkflowStage.PROCESSING):
        st.subheader("🎉 Processing Summary & Quality Gate")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cohort Clients", f"{result.total_cohort:,}")
        m2.metric("Active KPLHIV", f"{result.active_kplhiv:,}")
        m3.metric(
            "DQA Exceptions",
            f"{result.total_dqa_exceptions:,}",
            delta=f"{result.critical_dqa_count} Critical" if result.critical_dqa_count > 0 else "Clean",
            delta_color="inverse" if result.critical_dqa_count > 0 else "normal",
        )
        total_m = result.duration_seconds / 60.0
        m4.metric("Total Execution Time", f"{total_m:.2f} min", delta=f"{result.duration_seconds:.2f}s")

        with st.expander("⏱️ Granular Stage Timings (Minutes & Seconds)", expanded=True):
            stage_display_names = {
                "ingestion": "Stage 1: Ingestion",
                "cleaning": "Stage 2: Cleaning",
                "dqa": "Stage 3: DQA",
                "analytics": "Stage 4: Analytics",
                "reporting": "Stage 5: Reporting",
            }
            t_cols = st.columns(len(result.stage_timings))
            for i, (stg, duration) in enumerate(result.stage_timings.items()):
                mins = duration / 60.0
                label = stage_display_names.get(stg, stg.title())
                t_cols[i].metric(label=label, value=f"{mins:.2f} min", delta=f"{duration:.2f}s")

        st.divider()

        # Strict sequential guidance per Master Brief §4.1: Processing -> Data Quality
        st.markdown("#### Next Step")
        st.info("👉 **Prerequisite Notice:** You must review Data Quality exceptions before proceeding to the Dashboard.", icon="ℹ️")

        if st.button("🛡️ Continue to Data Quality Review ➡️", type="primary", use_container_width=True):
            st.switch_page("ui/data_quality.py")


render_processing()
