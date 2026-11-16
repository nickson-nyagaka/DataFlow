"""DATAFLOW Processing Page — Automated Analytical Pipeline Execution.

Primary Audience: Monitoring & Evaluation (M&E) Specialists, Data Officers, Lead Analysts.
Primary Question: "How is the automated analytical pipeline executing, are all stages progressing reliably, and what are the completion timings?"

Strictly adheres to Master Brief §7, §8, §9, §10 and Decisions D-040/D-041:
- Scoped presentation design system mirroring Dashboard and Analytics (keyed containers, cards, hover lift).
- Real-time event-driven execution monitoring for all five analytical stages with duration tracking in minutes & seconds.
- Mathematically normalized overall pipeline progress.
- Strict workflow gating: transitions to PROCESSED and unlocks Data Quality review.
"""

from __future__ import annotations

import html
import re
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root takes precedence in sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] != _ROOT:
    if _ROOT in sys.path:
        sys.path.remove(_ROOT)
    sys.path.insert(0, _ROOT)

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from core.exceptions import ProcessingStageError  # noqa: E402
from core.runner import run_full_pipeline  # noqa: E402
from core.workflow_manager import WorkflowStage  # noqa: E402
from ui.session import (  # noqa: E402
    advance_workflow_stage,
    render_access_guard,
)

# =============================================================================
# PRESENTATION DESIGN SYSTEM (display-only: scoped CSS, cards, hero, badges)
# =============================================================================
_ACCENT_BLUE = "#3B82F6"
_ACCENT_VIOLET = "#8B5CF6"
_ACCENT_TEAL = "#14B8A6"
_ACCENT_GREEN = "#22C55E"
_ACCENT_AMBER = "#F59E0B"
_ACCENT_RED = "#EF4444"

_PROCESSING_CSS = """
<style>
/* ---- hero banner ---- */
.dfx-hero {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 16px;
    padding: 20px 26px; margin: 4px 0 18px 0;
    border-radius: 18px;
    border: 1px solid rgba(128, 128, 128, 0.25);
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(139, 92, 246, 0.14));
}
.dfx-hero .title { font-size: 1.25rem; font-weight: 700; margin: 0 0 4px 0; }
.dfx-hero .sub { font-size: 0.88rem; opacity: 0.78; }
.dfx-hero .pills { display: flex; flex-wrap: wrap; gap: 8px; }

/* ---- pills / badges ---- */
.dfx-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 999px;
    font-size: 0.82rem; font-weight: 700;
    border: 1px solid rgba(128, 128, 128, 0.35);
    background: rgba(128, 128, 128, 0.10);
}
.dfx-pill.ok   { background: rgba(34, 197, 94, 0.15);  border-color: rgba(34, 197, 94, 0.55); }
.dfx-pill.warn { background: rgba(245, 158, 11, 0.16); border-color: rgba(245, 158, 11, 0.55); }
.dfx-pill.bad  { background: rgba(239, 68, 68, 0.15);  border-color: rgba(239, 68, 68, 0.55); }
.dfx-pill.info { background: rgba(59, 130, 246, 0.14); border-color: rgba(59, 130, 246, 0.45); }
.dfx-pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 14px 0; }

.dfx-badges { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 14px 0; }
.dfx-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 12px; border-radius: 999px;
    font-size: 0.80rem; font-weight: 600;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.35);
}
.dfx-badge.active {
    background: rgba(34, 197, 94, 0.15);
    border-color: rgba(34, 197, 94, 0.45);
}

/* ---- metric cards (Job Specs & Post-Processing Summary) ---- */
.st-key-job_cards [data-testid="stMetric"],
.st-key-proc_cards [data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.07);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-left: 6px solid #3B82F6;
    border-radius: 14px;
    padding: 16px 20px 14px 20px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.st-key-job_cards [data-testid="stMetric"]:hover,
.st-key-proc_cards [data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
}
.st-key-job_cards [data-testid="stMetricLabel"] p,
.st-key-proc_cards [data-testid="stMetricLabel"] p {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.75;
}
.st-key-job_cards [data-testid="stMetricValue"],
.st-key-proc_cards [data-testid="stMetricValue"] {
    font-size: 1.95rem;
    font-weight: 700;
    line-height: 1.15;
}

/* Card left border accents */
.st-key-job_cards [data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] { border-left-color: #3B82F6; }
.st-key-job_cards [data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { border-left-color: #8B5CF6; }
.st-key-job_cards [data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { border-left-color: #14B8A6; }
.st-key-job_cards [data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { border-left-color: #F59E0B; }

.st-key-proc_cards [data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] { border-left-color: #3B82F6; }
.st-key-proc_cards [data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { border-left-color: #8B5CF6; }
.st-key-proc_cards [data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { border-left-color: #F59E0B; }
.st-key-proc_cards [data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { border-left-color: #22C55E; }

/* ---- stage ribbon container ---- */
.dfx-stage-box {
    background: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.20);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
}

/* ---- framed expanders & charts ---- */
[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid rgba(128, 128, 128, 0.22);
}
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(128, 128, 128, 0.22);
}

/* ---- next-step container ---- */
.st-key-next_section {
    border: 1px solid rgba(59, 130, 246, 0.35);
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(139, 92, 246, 0.06));
    border-radius: 16px;
    padding: 18px 22px 14px 22px;
    margin-top: 14px;
}
</style>
"""


def _section_container(key: str):
    """Keyed container so scoped styles only target this block."""
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


def _esc(val: object) -> str:
    return html.escape(str(val))


def _timings_figure(timings: dict) -> go.Figure:
    """Compact horizontal bar chart of stage execution times."""
    stages = [str(k).title() for k in timings.keys()]
    secs = list(timings.values())
    fig = go.Figure(
        go.Bar(
            y=stages,
            x=secs,
            orientation="h",
            marker=dict(color=_ACCENT_TEAL, line=dict(width=0)),
            text=[f"{v:.3f}s" for v in secs],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:.3f}s<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(220, 46 * len(stages) + 60),
        margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=13),
        showlegend=False,
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(128,128,128,0.20)")
    return fig


def render_processing() -> None:
    st.title("⚙️ Automated Pipeline Processing")
    st.caption("Analytical Execution Engine — Orchestrate automated ingestion, cleaning, data quality assurance, and reporting.")

    # Guard check
    if not render_access_guard("Processing"):
        return

    # Inject Scoped Presentation Stylesheet
    st.markdown(_PROCESSING_CSS, unsafe_allow_html=True)

    # 1. Resolve active session context and uploaded file
    file_bytes = st.session_state.get("uploaded_file_bytes")
    file_name = st.session_state.get("uploaded_file_name", "cohort_register.xlsx")
    file_hash = st.session_state.get("uploaded_file_hash", "")
    population = st.session_state.get("population")
    period_mode = st.session_state.get("period_mode")
    mask_ident = st.session_state.get("mask_identifiers", False)

    prior_result = st.session_state.get("pipeline_result")
    if prior_result is not None and getattr(prior_result, "input_file_hash", "") != file_hash:
        prior_result = None

    if not population:
        for p_cand in ["PWID", "MSM", "TG", "VP", "FSW"]:
            if re.search(rf"(?:^|[\s_\-.\(\)\[\]]){p_cand}(?:$|[\s_\-.\(\)\[\]])", file_name.upper()):
                population = p_cand
                break
    if not population:
        population = "FSW"

    if not period_mode:
        period_mode = "SEM"

    if not file_bytes and not prior_result:
        st.warning(
            "⚠️ **No active cohort register found in memory.** Please return to the Upload page to upload a workbook.",
            icon="⚠️",
        )
        if st.button("⬅️ Go to Upload Data", type="primary"):
            st.switch_page("ui/upload.py")
        return

    # 2. Executive Hero Banner
    is_done = prior_result is not None
    status_text = "Completed & Verified" if is_done else "Ready to Execute"
    status_cls = "ok" if is_done else "info"

    st.markdown(
        f"""
        <div class="dfx-hero">
            <div>
                <div class="title">Automated Analytical Pipeline Processing</div>
                <div class="sub">
                    📄 <b>{_esc(file_name)}</b> &nbsp;·&nbsp; 👥 <b>{_esc(population)}</b> &nbsp;·&nbsp; 🗓️ <b>{_esc(period_mode)}</b>
                </div>
            </div>
            <div class="pills">
                <span class="dfx-pill {status_cls}">⚡ {status_text}</span>
                <span class="dfx-pill info">🔒 Masking: {'Active' if mask_ident else 'Unmasked'}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Job Specification Cards (Claude's KPI card format)
    with _section_container("job_cards"):
        j1, j2 = st.columns(2)
        j1.metric("Target Population", population, delta="Typology")
        j2.metric("Reporting Period", period_mode, delta="Standard")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. Action Controls Container
    with st.container(border=True):
        start_run = False
        force_run = False

        if prior_result:
            col_btn, col_force = st.columns([1, 1])
            with col_btn:
                if st.button("🔄 Re-run Processing Pipeline", type="primary", use_container_width=True):
                    start_run = True
                    force_run = True
            with col_force:
                if st.button("⚡ Instant Reload from Cache", use_container_width=True):
                    start_run = True
                    force_run = False
        else:
            if st.button("🚀 Run Automated Processing Pipeline", type="primary", use_container_width=True):
                start_run = True
                force_run = True

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 5. Live Background System Activity Console
    st.markdown("### 🖥️ System Background Activity & Execution Console")
    console_placeholder = st.empty()
    activity_logs: list[str] = st.session_state.get("activity_logs", [])
    if not activity_logs:
        if prior_result:
            activity_logs = [
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Active verified pipeline result loaded: {prior_result.input_file_name} ({prior_result.population}).",
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Cohort clients: {prior_result.total_cohort:,} | Active KPLHIV: {prior_result.active_kplhiv:,}.",
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] DQA exceptions: {prior_result.total_dqa_exceptions:,} ({prior_result.critical_dqa_count} Critical).",
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] All 5 analytical stages verified in {prior_result.duration_seconds:.2f}s.",
            ]
        else:
            activity_logs = [
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Engine ready for {population} ({period_mode}) cohort register.",
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Source workbook: {file_name}.",
                f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Ready to execute analytical pipeline stages...",
            ]
    console_placeholder.code("\n".join(activity_logs), language="bash")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 6. Pipeline Execution Progress Ribbons
    st.markdown("### 📊 Pipeline Stage Execution Ribbons")

    overall_container = st.container()
    stages_container = st.container()

    stage_meta = [
        ("ingestion", "📥 Stage 1: Workbook Ingestion", "Reading register & KPLHIV tracking worksheets"),
        ("cleaning", "🧹 Stage 2: Data Cleaning & Normalization", "Vectorized cleaning, date standardisation & normalized geography"),
        ("dqa", "🛡️ Stage 3: Data Quality Assessment (DQA)", "Evaluating demographic, clinical, and commodity validation rules"),
        ("analytics", "📈 Stage 4: Analytical Calculations", "Calculating cascade indicators, summary tables & age/sex disaggregations"),
        ("reporting", "📦 Stage 5: Reporting Package Assembly", "Assembling Master Multi-Tab Excel Workbook & Modular ZIP packages"),
    ]

    with overall_container:
        st.markdown("##### ⏱️ Overall Pipeline Progress")
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

    # 7. Pipeline Execution Callback & Handler
    if start_run or force_run:
        advance_workflow_stage(WorkflowStage.PROCESSING)

        activity_logs = []

        def on_pipeline_progress(snapshot: dict[str, Any]) -> None:
            ov_pct = snapshot.get("overall_progress", 0.0)
            overall_progress_bar.progress(ov_pct / 100.0)
            overall_status_text.markdown(f"**Progress:** `{int(ov_pct)}% COMPLETED`")

            curr_time = time.strftime("%H:%M:%S")

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

                    # Stream background operation to live console
                    if status == "RUNNING":
                        log_msg = f"[{curr_time}] ⏳ [{s_id.upper()}] {s_data['current_operation']}"
                        if not activity_logs or activity_logs[-1] != log_msg:
                            activity_logs.append(log_msg)
                            console_placeholder.code("\n".join(activity_logs[-10:]), language="bash")
                    elif status == "COMPLETED":
                        log_msg = f"[{curr_time}] ✓ [{s_id.upper()}] {s_data['current_operation']} ({dur_s:.2f}s)"
                        if not activity_logs or activity_logs[-1] != log_msg:
                            activity_logs.append(log_msg)
                            console_placeholder.code("\n".join(activity_logs[-10:]), language="bash")

        try:
            result = run_full_pipeline(
                file_source=file_bytes or file_name,
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

            # Final success log
            final_time = time.strftime("%H:%M:%S")
            activity_logs.append(f"[{final_time}] ✅ [PIPELINE SUCCESS] Processed {result.total_cohort:,} clients | Completed in {result.duration_seconds:.2f}s.")
            console_placeholder.code("\n".join(activity_logs[-10:]), language="bash")
            st.session_state["activity_logs"] = activity_logs

            # Ensure all UI bars display 100% on completion
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

            if isinstance(exc, ProcessingStageError):
                st.error(exc.to_actionable_markdown(), icon="❌")
                if exc.technical_details:
                    with st.expander("🛠️ Technical Diagnostic Details (for Developers)", expanded=False):
                        st.code(exc.technical_details, language="text")
            else:
                import traceback

                st.error(
                    f"### ❌ Processing Pipeline Interrupted\n\n"
                    f"**Problem:** {exc}\n\n"
                    f"**Likely Cause:** An unexpected data structure inconsistency occurred during execution.\n\n"
                    f"**How to fix this:**\n"
                    f"1. Check that the uploaded workbook conforms to the official template structure.\n"
                    f"2. Ensure all column headers and data types match expected requirements.\n"
                    f"3. Return to the Upload page to replace or re-upload the workbook.",
                    icon="❌",
                )
                with st.expander("🛠️ Technical Diagnostic Details (for Developers)", expanded=False):
                    st.code(traceback.format_exc(), language="text")

            err_col1, err_col2 = st.columns(2)
            with err_col1:
                if st.button("⬅️ Return to Upload & Replace Workbook", type="primary", use_container_width=True):
                    advance_workflow_stage(WorkflowStage.EMPTY)
                    st.switch_page("ui/upload.py")
            with err_col2:
                if st.button("🔄 Retry Processing", use_container_width=True):
                    st.rerun()
            return

    # 7. Render Processing Summary & Quality Gate
    current_stage = st.session_state.get("workflow_stage", WorkflowStage.EMPTY)
    result = st.session_state.get("pipeline_result")
    if result is not None and getattr(result, "input_file_hash", "") != file_hash:
        result = None

    if result is not None and current_stage not in (WorkflowStage.EMPTY, WorkflowStage.UPLOADED, WorkflowStage.PROCESSING):
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.subheader("🎉 Processing Summary & Quality Gate")
        st.caption("Consolidated analytical output statistics ready for supervisory data quality review.")

        with _section_container("proc_cards"):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Cohort Clients", f"{result.total_cohort:,}", help="Total deduplicated clients in registered cohort.")
            m2.metric("Active KPLHIV", f"{result.active_kplhiv:,}", help="Known positive clients active on ART.")
            m3.metric(
                "DQA Exceptions",
                f"{result.total_dqa_exceptions:,}",
                delta=f"{result.critical_dqa_count} Critical" if result.critical_dqa_count > 0 else "Clean",
                delta_color="inverse" if result.critical_dqa_count > 0 else "normal",
                help="Data quality assurance exceptions found.",
            )
            total_m = result.duration_seconds / 60.0
            m4.metric("Execution Duration", f"{total_m:.2f} min", delta=f"{result.duration_seconds:.2f}s", help="Wall-clock execution duration.")

        with st.expander("⏱️ Granular Stage Timings & Performance Breakdown", expanded=True):
            col_meta, col_chart = st.columns([1, 1])
            with col_meta:
                st.markdown("#### Stage Timings")
                stage_display_names = {
                    "ingestion": "Stage 1: Ingestion",
                    "cleaning": "Stage 2: Cleaning",
                    "dqa": "Stage 3: DQA",
                    "analytics": "Stage 4: Analytics",
                    "reporting": "Stage 5: Reporting",
                }
                for stg, duration in result.stage_timings.items():
                    mins = duration / 60.0
                    label = stage_display_names.get(stg, stg.title())
                    st.write(f"• **{label}:** `{mins:.2f} min` ({duration:.3f}s)")
            with col_chart:
                if result.stage_timings:
                    st.plotly_chart(_timings_figure(result.stage_timings), use_container_width=True, config={"displayModeBar": False})

        # 8. Workflow Progression — Proceed to Data Quality Review
        with _section_container("next_section"):
            st.subheader("🏁 Next Workflow Step")
            st.caption("Pipeline execution complete. Proceed to supervisory Data Quality Assurance (DQA) review.")

            col_inf, col_btn = st.columns([2, 1])
            with col_inf:
                st.info("ℹ️ Next Stage: Review clinical exceptions, missing demographics, and validation rules in Data Quality.")
            with col_btn:
                if st.button("🛡️ Proceed to Data Quality Review ➡️", type="primary", use_container_width=True):
                    st.switch_page("ui/data_quality.py")


render_processing()
