"""DATAFLOW Data Quality Assurance (DQA) Page.

Implements Master Brief §11 and Decision D-042:
- Exception review grouped by severity (Critical, Major, Minor).
- Aggregate summary table (rule ID, name, severity, count, remediation).
- Multi-field override protocol for Critical exceptions requiring authorized name and >= 20 char reason per rule.
- File-hash and count anchoring (data modifications cancel override).
- Append-only audit logging in runtime/audit/override_log.jsonl without personal identifiers.
- Always allows download of DQA exceptions workbook for facility remediation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.override import OverrideManager
from core.validation import RULE_DEFINITIONS
from reporting.dqa_exporter import export_dqa_exceptions_workbook
from ui.session import render_access_guard


def render_data_quality() -> None:
    st.title("🛡️ Data Quality Assurance (DQA)")
    st.caption("Comprehensive data quality exception review, and supervisory override controls.")

    if not render_access_guard("Data Quality"):
        return

    result = st.session_state.get("pipeline_result")
    if not result:
        st.warning("No pipeline results available. Please run processing first.")
        return

    dqa = result.dqa_results
    file_hash = result.input_file_hash
    override_mgr: OverrideManager = st.session_state.get("override_manager")
    if override_mgr is None:
        override_mgr = OverrideManager()
        st.session_state["override_manager"] = override_mgr

    # 1. Severity Summary Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Critical (Blocking)", f"{dqa.severity_counts.get('Critical', 0):,}")
    c2.metric("Major", f"{dqa.severity_counts.get('Major', 0):,}")
    c3.metric("Minor", f"{dqa.severity_counts.get('Minor', 0):,}")
    c4.metric("Total Exceptions", f"{dqa.total_exceptions:,}")

    st.divider()

    # 2. Critical DQA Warning & Gating Status
    critical_counts = dqa.get_critical_counts()
    block_on_crit = st.session_state.get("block_on_critical", True)
    is_blocked, blocking_reasons, is_prov = override_mgr.check_export_status(
        dqa_results=dqa,
        file_hash=file_hash,
        block_on_critical=block_on_crit,
    )

    if critical_counts:
        if is_blocked:
            st.error(
                f"🚨 **Report Export Blocked by Critical Exceptions!**\n\n"
                f"{blocking_reasons[0]}\n\n"
                "Summary and ZIP exports are disabled. Correct the source register and re-upload, "
                "or authorize a supervisory override below.",
                icon="🚨",
            )
        else:
            st.warning(
                "⚠️ **Critical Exceptions Overridden (PROVISIONAL Mode):**\n\n"
                "All Critical exceptions have been authorized with supervisory justification. "
                "Exported workbooks are unlocked and will be stamped `PROVISIONAL`.",
                icon="⚠️",
            )

    elif dqa.total_exceptions == 0:
        st.success(
            "✅ **Clean Register:** No data quality exceptions detected. All records passed validation.",
            icon="✅",
        )

    # 3. Supervisory Override Form (Decision D-042)
    if critical_counts and block_on_crit:
        with st.expander(
            "✍️ Authorize Critical DQA Override (Supervisory Access)", expanded=is_blocked
        ):
            st.markdown(
                "Supervisors may authorize provisional export by recording their full name and a "
                "clinical justification of at least 20 characters per Critical rule. "
                "This action is logged in `runtime/audit/override_log.jsonl` with zero client identifiers."
            )

            # Find unoverridden rules
            unoverridden = [
                r
                for r, cnt in critical_counts.items()
                if not (
                    r in override_mgr.overrides
                    and override_mgr.overrides[r].is_valid_for(file_hash, cnt)
                )
            ]

            if not unoverridden:
                st.success("All Critical rules for this workbook have valid active overrides.")
            else:
                with st.form("override_form", clear_on_submit=False):
                    rule_to_override = st.selectbox(
                        "Critical Rule to Override",
                        options=unoverridden,
                        format_func=lambda r: (
                            f"{r} ({critical_counts[r]} exceptions) — {RULE_DEFINITIONS.get(r, None).name if r in RULE_DEFINITIONS else r}"
                        ),
                    )
                    auth_name = st.text_input(
                        "Authorized Supervisor Name *",
                        placeholder="e.g. Dr. Jane Doe (Program Lead)",
                    )
                    auth_reason = st.text_area(
                        "Clinical / Operational Justification * (min 20 characters)",
                        placeholder="Explain why records are accepted provisionally and remediation steps planned...",
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

    # 4. Aggregate Exceptions Table
    st.subheader("📋 DQA Exceptions Aggregate Registry")

    if not dqa.exceptions_df.empty:
        # Build aggregate view (Rule ID, Rule Name, Severity, Target Sheet, Exception Count)
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
                    "Suggested Action": rule_def.suggested_action if rule_def else "Review record",
                }
            )

        agg_df = pd.DataFrame(agg_rows)

        # Severity filter
        sev_choice = st.radio(
            "Filter by Severity",
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
        st.info("No exceptions to display.")

    # 5. Standalone DQA Exceptions Workbook Download (Always available per D-042)
    st.divider()
    st.subheader("📥 Export DQA Exceptions Workbook")
    st.caption(
        "Providers and Sub-Recipients can use this standalone workbook to trace and correct invalid cohort entries."
    )

    dqa_path = (
        Path("runtime/temporary") / f"dqa_exceptions_{result.population}_{result.period_mode}.xlsx"
    )
    export_dqa_exceptions_workbook(
        exceptions_df=dqa.exceptions_df,
        output_path=dqa_path,
    )

    if dqa_path.exists():
        with open(dqa_path, "rb") as f:
            dqa_bytes = f.read()

        st.download_button(
            label="Download Standalone DQA Exceptions Workbook (.xlsx) 📥",
            data=dqa_bytes,
            file_name=f"DATAFLOW_DQA_Exceptions_{result.population}_{result.period_mode}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


render_data_quality()
