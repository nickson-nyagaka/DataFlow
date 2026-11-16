"""DATAFLOW Data Quality Assurance (DQA) Page — Clinical Integrity & Rule Audit.

Primary Audience: Monitoring & Evaluation (M&E) Specialists, Clinical Supervisors, Data Officers.
Primary Question: "What data quality anomalies exist across demographic and clinical fields, are there critical exceptions, and what remediation actions are required?"

Strictly adheres to Master Brief §11 and Decisions D-040, D-041, D-042:
- Scoped presentation design system mirroring Dashboard and Analytics (keyed containers, cards, hover lift).
- Exception review grouped by severity (Critical, Major, Minor) with distinct left-accent colors.
- Aggregate summary table (rule ID, name, severity, count, remediation).
- Multi-field supervisory override protocol for Critical exceptions requiring authorized name and >= 20 char reason.
- Standalone DQA exceptions workbook generation and download for facility-level follow-up.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

# Ensure project root takes precedence in sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] != _ROOT:
    if _ROOT in sys.path:
        sys.path.remove(_ROOT)
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from core.override import OverrideManager  # noqa: E402
from core.validation import RULE_DEFINITIONS  # noqa: E402
from core.workflow_manager import WorkflowStage  # noqa: E402
from reporting.dqa_exporter import export_dqa_exceptions_workbook  # noqa: E402
from ui.session import (  # noqa: E402
    advance_workflow_stage,
    get_active_pipeline_result,
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

_DQA_CSS = """
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
.dfx-hero.bad {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.16), rgba(245, 158, 11, 0.12));
    border-color: rgba(239, 68, 68, 0.35);
}
.dfx-hero.warn {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.16), rgba(59, 130, 246, 0.12));
    border-color: rgba(245, 158, 11, 0.35);
}
.dfx-hero.ok {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.16), rgba(59, 130, 246, 0.12));
    border-color: rgba(34, 197, 94, 0.40);
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
.dfx-badge.crit { background: rgba(239, 68, 68, 0.14); border-color: rgba(239, 68, 68, 0.45); }
.dfx-badge.major { background: rgba(245, 158, 11, 0.14); border-color: rgba(245, 158, 11, 0.45); }

/* ---- scoped metric cards ---- */
.st-key-dqa_cards [data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.07);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-left: 6px solid #3B82F6;
    border-radius: 14px;
    padding: 16px 20px 14px 20px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.st-key-dqa_cards [data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
}
.st-key-dqa_cards [data-testid="stMetricLabel"] p {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.75;
}
.st-key-dqa_cards [data-testid="stMetricValue"] {
    font-size: 2.0rem;
    font-weight: 700;
    line-height: 1.15;
}

/* Severity border colors */
.st-key-dqa_cards [data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] { border-left-color: #EF4444; }
.st-key-dqa_cards [data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { border-left-color: #F59E0B; }
.st-key-dqa_cards [data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { border-left-color: #3B82F6; }
.st-key-dqa_cards [data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { border-left-color: #8B5CF6; }

/* ---- framed expanders & dataframes ---- */
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


def render_data_quality() -> None:
    st.title("🛡️ Data Quality Assurance (DQA)")
    st.caption("Clinical Integrity & Rule Audit — Exception review grouped by severity, supervisory overrides, and remediation.")

    # Guard check
    if not render_access_guard("Data Quality"):
        return

    # 1. Retrieve active session pipeline result (resolving current upload if present)
    result = get_active_pipeline_result()
    if not result:
        st.warning("⚠️ No processed cohort records available. Please run processing first.", icon="⚠️")
        return

    # Inject Scoped Presentation Stylesheet
    st.markdown(_DQA_CSS, unsafe_allow_html=True)

    dqa = result.dqa_results
    file_hash = result.input_file_hash
    population = result.population
    period_mode = result.period_mode
    file_name = result.input_file_name

    crit_n = dqa.severity_counts.get("Critical", 0)
    major_n = dqa.severity_counts.get("Major", 0)
    minor_n = dqa.severity_counts.get("Minor", 0)
    total_exceptions = dqa.total_exceptions

    override_mgr: OverrideManager = st.session_state.get("override_manager")
    if override_mgr is None:
        override_mgr = OverrideManager()
        st.session_state["override_manager"] = override_mgr

    critical_counts = dqa.get_critical_counts()
    block_on_crit = st.session_state.get("block_on_critical", False)
    is_blocked, blocking_reasons, is_prov = override_mgr.check_export_status(
        dqa_results=dqa,
        file_hash=file_hash,
        block_on_critical=block_on_crit,
    )

    # 2. Executive Hero Banner
    hero_cls = "bad" if crit_n > 0 else ("warn" if major_n > 0 else "ok")
    status_label = f"{crit_n} Critical Exceptions Detected" if crit_n > 0 else ("Review Recommended" if major_n > 0 else "Verified Clean Register")

    st.markdown(
        f"""
        <div class="dfx-hero {hero_cls}">
            <div>
                <div class="title">Data Quality Assurance & Clinical Verification</div>
                <div class="sub">
                    👥 <b>{_esc(population)}</b> &nbsp;·&nbsp; 🗓️ <b>{_esc(period_mode)}</b> &nbsp;·&nbsp; 📄 <b>{_esc(file_name)}</b>
                </div>
            </div>
            <div class="pills">
                <span class="dfx-pill {'bad' if crit_n > 0 else 'ok'}">🛡️ {status_label}</span>
                <span class="dfx-pill info">📋 {total_exceptions:,} Total Exceptions</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Context Badges
    st.markdown(
        f"""
        <div class="dfx-badges">
            <span class="dfx-badge crit">🔴 {crit_n:,} Critical</span>
            <span class="dfx-badge major">🟠 {major_n:,} Major</span>
            <span class="dfx-badge">🔵 {minor_n:,} Minor</span>
            <span class="dfx-badge">🔑 Hash: {_esc(file_hash[:16])}...</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Severity Summary Metrics (Claude's 4-card grid format)
    with _section_container("dqa_cards"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            label="Critical (Blocking)",
            value=f"{crit_n:,}",
            delta="Requires Action" if crit_n > 0 else "0 Defects",
            delta_color="inverse" if crit_n > 0 else "normal",
            help="High-severity data discrepancies (e.g. invalid dates, age out of range, missing core IDs).",
        )
        c2.metric(
            label="Major Exceptions",
            value=f"{major_n:,}",
            delta="Review" if major_n > 0 else "Clean",
            delta_color="inverse" if major_n > 0 else "normal",
            help="Clinical and service linkage inconsistencies.",
        )
        c3.metric(
            label="Minor Exceptions",
            value=f"{minor_n:,}",
            delta="Informational",
            delta_color="off",
            help="Formatting anomalies, extra spaces, or non-standard casing.",
        )
        c4.metric(
            label="Total DQA Findings",
            value=f"{total_exceptions:,}",
            delta=f"{result.total_cohort:,} Records Evaluated",
            delta_color="off",
            help="Sum of all data quality exceptions across all evaluated rules.",
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. Critical Warning & Export Advisory Notice
    if critical_counts:
        st.warning(
            f"⚠️ **Critical Data Quality Notice ({crit_n:,} exception records detected):**\n\n"
            f"{blocking_reasons[0] if blocking_reasons else 'Critical exceptions were detected in the source cohort.'}\n\n"
            "**Notice:** All master Excel reporting packages and export workbooks remain accessible for download on the Export Reports page. "
            "Supervisors may log a formal clinical review or operational justification below if required.",
            icon="⚠️",
        )
    elif is_prov:
        st.info(
            "ℹ️ **PROVISIONAL Mode Active:** Critical exceptions acknowledged under supervisory override. Master Excel packages will be stamped `PROVISIONAL`.",
            icon="ℹ️",
        )
    elif total_exceptions == 0:
        st.success(
            "✅ **Clean Quality Verification:** 0 Data Quality exceptions detected across all rules. All cohort records meet approved standards.",
            icon="✅",
        )

    # 5. Supervisory Override Protocol (Decision D-042)
    if critical_counts and block_on_crit:
        with st.expander("✍️ Authorize Critical DQA Override (Supervisory Access)", expanded=is_blocked):
            st.markdown(
                "Supervisors may authorize provisional export by recording their full name and an "
                "operational / clinical justification of at least 20 characters per Critical rule. "
                "This action is logged in `runtime/audit/override_log.jsonl` with zero client identifiers."
            )

            unoverridden = [
                r
                for r, cnt in critical_counts.items()
                if not (
                    r in override_mgr.overrides
                    and override_mgr.overrides[r].is_valid_for(file_hash, cnt)
                )
            ]

            if not unoverridden:
                st.success("✅ All Critical rules for this workbook have valid active overrides.")
            else:
                with st.form("override_form", clear_on_submit=False):
                    rule_to_override = st.selectbox(
                        "Critical Rule to Override",
                        options=unoverridden,
                        format_func=lambda r: (
                            f"{r} ({critical_counts[r]} exceptions) — {RULE_DEFINITIONS.get(r).name if r in RULE_DEFINITIONS else r}"
                        ),
                    )
                    auth_name = st.text_input(
                        "Authorized Supervisor Name *",
                        placeholder="e.g. Dr. Jane Doe (Program Lead / M&E Director)",
                    )
                    auth_reason = st.text_area(
                        "Clinical / Operational Justification * (min 20 characters)",
                        placeholder="Explain why records are accepted provisionally and describe remediation steps...",
                    )
                    submitted = st.form_submit_button("Authorize and Log Override", type="primary")

                    if submitted:
                        try:
                            override_mgr.record_override(
                                rule_id=rule_to_override,
                                authorized_by=auth_name,
                                reason=auth_reason,
                                file_hash=file_hash,
                                exception_count=critical_counts[rule_to_override],
                            )
                            st.success(
                                f"✅ Override recorded for `{rule_to_override}`. Logged to audit trail.",
                                icon="✅",
                            )
                            st.rerun()
                        except ValueError as err:
                            st.error(f"❌ Override rejected: {err}", icon="❌")

    st.divider()

    # 6. Aggregate Exceptions Registry Table
    st.subheader("📋 DQA Exceptions Aggregate Registry")
    st.caption("Detailed catalog of all triggered rules, affected sheets, exception counts, and recommended actions.")

    if not dqa.exceptions_df.empty:
        agg_rows = []
        for rule_id, count in dqa.rule_counts.items():
            rule_def = RULE_DEFINITIONS.get(rule_id)
            agg_rows.append(
                {
                    "Rule ID": rule_id,
                    "Rule Name": rule_def.name if rule_def else rule_id,
                    "Severity": rule_def.severity if rule_def else "Unknown",
                    "Sheet Target": rule_def.sheet_target if rule_def else "Register",
                    "Exceptions Count": count,
                    "Suggested Action": rule_def.suggested_action if rule_def else "Review record in Excel",
                }
            )

        agg_df = pd.DataFrame(agg_rows)

        # Severity filter
        sev_choice = st.radio(
            "Filter Registry by Severity",
            options=["All", "Critical", "Major", "Minor"],
            horizontal=True,
        )
        if sev_choice != "All":
            agg_df = agg_df[agg_df["Severity"] == sev_choice]

        st.dataframe(
            agg_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Exceptions Count": st.column_config.NumberColumn(format="%d"),
            },
        )
    else:
        st.info("ℹ️ No exceptions recorded for this cohort register.")

    # 7. Standalone DQA Exceptions Workbook Download (Always accessible per Decision D-042)
    st.divider()
    st.subheader("📥 Export Standalone DQA Exceptions Workbook")
    st.caption("Providers, Sub-Recipients, and facility teams can use this workbook to trace and correct invalid cohort entries in Excel.")

    dqa_path = Path("runtime/temporary") / f"dqa_exceptions_{population}_{period_mode}.xlsx"
    export_dqa_exceptions_workbook(
        exceptions_df=dqa.exceptions_df,
        output_path=dqa_path,
    )

    if dqa_path.exists():
        with open(dqa_path, "rb") as f:
            dqa_bytes = f.read()

        d_col1, d_col2 = st.columns([1, 1])
        with d_col1:
            st.download_button(
                label=f"📥 Download Standalone DQA Exceptions Workbook ({population}_{period_mode}.xlsx)",
                data=dqa_bytes,
                file_name=f"DATAFLOW_DQA_Exceptions_{population}_{period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="secondary",
            )
        with d_col2:
            st.caption(f"✓ Standalone remedial workbook containing {len(dqa.exceptions_df):,} line-level exception rows.")

    # 8. Workflow Progression: Continue to Dashboard
    with _section_container("next_section"):
        st.subheader("🏁 Next Workflow Step")
        st.caption("Acknowledge review of the DQA findings above to unlock the Executive Performance Dashboard.")

        col_ack, col_btn = st.columns([2, 1])
        with col_ack:
            st.info("ℹ️ Proceeding to the Dashboard certifies that data quality findings have been reviewed for this cohort.")
        with col_btn:
            if st.button("📊 Continue to Dashboard ➡️", type="primary", use_container_width=True):
                st.session_state["dqa_reviewed"] = True
                advance_workflow_stage(WorkflowStage.DQA_REVIEWED)
                st.switch_page("ui/dashboard.py")


render_data_quality()
