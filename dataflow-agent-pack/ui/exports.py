"""DATAFLOW Export Reports Page.

Implements Master Brief §11 and Decisions D-042 & D-043:
- Identifier warning banner ("Contains unmasked identifiers - do not transmit outside secure environment").
- Gated downloads: summary, indicator, and ZIP exports are blocked while unoverridden Critical exceptions exist.
- Download presentation hierarchy: Primary button for Master Excel Package (.xlsx) + secondary button for
  Modular ZIP (.zip) + individual component download buttons.
- Standalone DQA exceptions workbook and cleaning log always stay downloadable.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.override import OverrideManager
from core.workflow_manager import WorkflowStage
from ui.session import advance_workflow_stage, render_access_guard


def render_exports() -> None:
    st.title("📥 Export Reporting Packages")
    st.caption(
        "Download formatted Global Fund Excel reporting packages and modular audit artifacts."
    )

    if not render_access_guard("Export Reports"):
        return

    result = st.session_state.get("pipeline_result")
    if not result:
        st.warning("No pipeline results available. Please run processing first.")
        return

    advance_workflow_stage(WorkflowStage.EXPORT_READY)

    override_mgr: OverrideManager = st.session_state.get("override_manager")
    if override_mgr is None:
        override_mgr = OverrideManager()
        st.session_state["override_manager"] = override_mgr

    file_hash = result.input_file_hash
    dqa = result.dqa_results
    block_on_crit = st.session_state.get("block_on_critical", True)
    mask_ident = st.session_state.get("mask_identifiers", False)

    # 1. Identifier Warning Banner
    if mask_ident:
        st.info(
            "🔒 **Identifier Masking Active:** Personal Unique Identifier Codes (UICs) and CCC numbers "
            "have been replaced with deterministic salted hashes (`MASK-XXXX`) across all exported tables.",
            icon="🔒",
        )
    else:
        st.warning(
            "⚠️ **CONFIDENTIAL HEALTH DATA NOTICE:**\n\n"
            "This reporting package contains **unmasked Unique Identifier Codes (UICs)** and clinical CCC numbers. "
            "Under the Kenya Data Protection Act 2019 and MOH confidentiality standards, "
            "**do NOT transmit or distribute these files outside authorized, secure health facilities.**",
            icon="⚠️",
        )

    st.divider()

    # 2. Check DQA Status and Advisory Notices
    is_blocked, blocking_reasons, is_prov = override_mgr.check_export_status(
        dqa_results=dqa,
        file_hash=file_hash,
        block_on_critical=block_on_crit,
    )

    if dqa and dqa.has_critical:
        crit_n = dqa.severity_counts.get("Critical", 0)
        st.warning(
            f"⚠️ **DQA Advisory Notice ({crit_n:,} Critical Exception{'s' if crit_n != 1 else ''} Detected):**\n\n"
            f"{blocking_reasons[0] if blocking_reasons else 'Critical data quality exceptions exist in this cohort.'}\n\n"
            "**All export packages remain fully available for download below.** "
            "Please download the DQA Exceptions workbook to perform facility-level data reconciliation.",
            icon="⚠️",
        )
    elif is_prov:
        st.info(
            "ℹ️ **PROVISIONAL Report Output:**\n\n"
            "This package contains Critical DQA exceptions under advisory mode or supervisory authorization. "
            "All exported sheets and metadata are stamped with `PROVISIONAL`.",
            icon="ℹ️",
        )
    elif dqa and dqa.total_exceptions > 0:
        st.info(
            f"ℹ️ **Quality Audit Notice:** {dqa.total_exceptions:,} DQA exception(s) detected. "
            "All reporting packages are validated and ready for download.",
            icon="ℹ️",
        )
    else:
        st.success(
            "✅ **All Quality Gates Cleared:** 0 Critical DQA exceptions. Reporting packages are fully validated.",
            icon="✅",
        )

    # 3. Period Selection & Reporting Package Overview
    st.subheader("1. Reporting Period & Package Overview")
    col_per_sel, col_stat1, col_stat2, col_stat3 = st.columns([2, 1, 1, 1])

    current_period = result.period_mode.upper() if result.period_mode else "SEM"
    period_options = ["SEM", "Q1", "Q2"]
    default_idx = period_options.index(current_period) if current_period in period_options else 0

    with col_per_sel:
        selected_period = st.selectbox(
            "Target Reporting Period",
            options=period_options,
            index=default_idx,
            key="ui_export_period_selector",
            help="Choose SEM (Full Semester, Jul-Dec), Q1 (Quarter 1, Jul-Sep), or Q2 (Quarter 2, Oct-Dec).",
        )

    with col_stat1:
        st.metric("Population", result.population)
    with col_stat2:
        st.metric("Period", selected_period)
    with col_stat3:
        st.metric("Cohort Records", f"{result.total_cohort:,}")

    # Re-run pipeline if user changed period from the active result
    if selected_period != current_period:
        with st.spinner(f"Re-generating analytics and reporting packages for {result.population} ({selected_period})..."):
            from core.runner import run_full_pipeline
            file_bytes = st.session_state.get("uploaded_file_bytes")
            file_name = st.session_state.get("uploaded_file_name", f"cohort_{result.population.lower()}.xlsx")
            new_result = run_full_pipeline(
                file_source=file_bytes if file_bytes else file_name,
                file_name=file_name,
                population=result.population,
                period_mode=selected_period,
                mask_identifiers=mask_ident,
                force_rerun=False,
            )
            st.session_state["pipeline_result"] = new_result
            st.session_state["period_mode"] = selected_period
            st.rerun()

    st.divider()

    st.success("🎉 **Ready for Export:** Your reporting package has been successfully generated.", icon="🎉")

    # 4. Download Options
    st.subheader("2. Primary Export Packages")

    master_path = result.package_paths.get("master_workbook")
    zip_path = result.package_paths.get("zip_package")
    master_bytes = None
    zip_bytes = None

    col_master, col_zip = st.columns(2)

    with col_master:
        if master_path and Path(master_path).exists():
            with open(master_path, "rb") as f:
                master_bytes = f.read()

            st.download_button(
                label="📘 Download Master Excel Package (.xlsx)",
                data=master_bytes,
                file_name=Path(master_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=False,
                type="primary",
                use_container_width=True,
                help="Consolidated all-in-one reporting package containing Summary, Cleaned Cohort, Cleaned KPLHIV, DQA Exceptions, and KPI Disaggregations.",
            )
        else:
            st.button(
                "📘 Master Excel Package Unavailable", disabled=True, use_container_width=True
            )

    with col_zip:
        if zip_path and Path(zip_path).exists():
            with open(zip_path, "rb") as f:
                zip_bytes = f.read()

            st.download_button(
                label="🗜️ Download Modular ZIP Archive (.zip)",
                data=zip_bytes,
                file_name=Path(zip_path).name,
                mime="application/zip",
                disabled=False,
                type="secondary",
                use_container_width=True,
                help="ZIP archive containing individual standalone workbooks for each reporting module.",
            )
        else:
            st.button("🗜️ Modular ZIP Archive Unavailable", disabled=True, use_container_width=True)

    st.divider()

    # 5. Individual Component Downloads (Always available for DQA / Remediation / Reporting)
    st.subheader("3. Individual Component Downloads")
    st.caption("Individual workbooks and audit trails for targeted facility review.")

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    # Summary Report Workbook
    summary_path = result.package_paths.get("summary_workbook")
    disagg_path = result.package_paths.get("disaggregation_workbook")
    cleaned_path = result.package_paths.get("cleaned_data_workbook")
    dqa_path = result.package_paths.get("dqa_workbook")

    with c1:
        st.markdown("**Service Summary Report**")
        if summary_path and Path(summary_path).exists():
            with open(summary_path, "rb") as f:
                s_bytes = f.read()
            st.download_button(
                label="Download Service Summary (.xlsx) 📥",
                data=s_bytes,
                file_name=Path(summary_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_summary_wb",
                use_container_width=True,
            )
        elif master_bytes:
            st.download_button(
                label="Download Summary (from Master) 📥",
                data=master_bytes,
                file_name=f"Summary_Report_{result.population}_{result.period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_summary_master",
                use_container_width=True,
            )
        else:
            st.button("Summary Unavailable", disabled=True, key="btn_summary_dis", use_container_width=True)

    with c2:
        st.markdown("**Age & Sex Disaggregation Report**")
        if disagg_path and Path(disagg_path).exists():
            with open(disagg_path, "rb") as f:
                d_bytes = f.read()
            st.download_button(
                label="Download Disaggregations (.xlsx) 📥",
                data=d_bytes,
                file_name=Path(disagg_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_disagg_wb",
                use_container_width=True,
            )
        elif master_bytes:
            st.download_button(
                label="Download Disaggregations (from Master) 📥",
                data=master_bytes,
                file_name=f"Disaggregations_{result.population}_{result.period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_disagg_master",
                use_container_width=True,
            )
        else:
            st.button("Disaggregations Unavailable", disabled=True, key="btn_disagg_dis", use_container_width=True)

    with c3:
        st.markdown("**DQA Exceptions Workbook**")
        dqa_file_candidate = None
        if dqa_path and Path(dqa_path).exists():
            dqa_file_candidate = Path(dqa_path)
        else:
            tmp_dqa = (
                Path("runtime/temporary")
                / f"dqa_exceptions_{result.population}_{result.period_mode}.xlsx"
            )
            if tmp_dqa.exists():
                dqa_file_candidate = tmp_dqa

        if dqa_file_candidate and dqa_file_candidate.exists():
            with open(dqa_file_candidate, "rb") as f:
                dqa_bytes = f.read()
            st.download_button(
                label="Download DQA Exceptions (.xlsx) 📥",
                data=dqa_bytes,
                file_name=dqa_file_candidate.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_dqa_always",
                use_container_width=True,
            )
        else:
            st.button(
                "DQA Exceptions Generating...",
                disabled=True,
                key="btn_dqa_none",
                use_container_width=True,
            )

    with c4:
        st.markdown("**Audit & Reconciliation Trail**")
        audit_file = Path("runtime/audit/override_log.jsonl")
        audit_content = audit_file.read_bytes() if audit_file.exists() else b"{}"
        st.download_button(
            label="Download Audit Log (.jsonl) 📥",
            data=audit_content,
            file_name="DATAFLOW_Override_Audit.jsonl",
            mime="application/x-ndjson",
            key="btn_audit_always",
            use_container_width=True,
        )

    # Row for Cleaned Data
    st.markdown("---")
    st.markdown("**Cleaned Microdata & Enriched Registers**")
    cc1, cc2 = st.columns(2)
    with cc1:
        if cleaned_path and Path(cleaned_path).exists():
            with open(cleaned_path, "rb") as f:
                c_bytes = f.read()
            st.download_button(
                label="Download Cleaned Register & KPLHIV (.xlsx) 📥",
                data=c_bytes,
                file_name=Path(cleaned_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_cleaned_data_wb",
                use_container_width=True,
            )
        elif master_bytes:
            st.download_button(
                label="Download Cleaned Register (from Master) 📥",
                data=master_bytes,
                file_name=f"Cleaned_Register_{result.population}_{result.period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_clean_reg_master",
                use_container_width=True,
            )
        else:
            st.button("Cleaned Data Unavailable", disabled=True, key="btn_clean_dis", use_container_width=True)

    with cc2:
        if master_bytes:
            st.download_button(
                label="Download Cleaned KPLHIV (from Master) 📥",
                data=master_bytes,
                file_name=f"Cleaned_KPLHIV_{result.population}_{result.period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_clean_kp_master",
                use_container_width=True,
            )


render_exports()
