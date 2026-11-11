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
from ui.session import render_access_guard


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

    # 2. Check Critical DQA Gating (Decision D-042)
    is_blocked, blocking_reasons, is_prov = override_mgr.check_export_status(
        dqa_results=dqa,
        file_hash=file_hash,
        block_on_critical=block_on_crit,
    )

    if is_blocked:
        st.error(
            f"🚫 **Summary & ZIP Exports Blocked by Critical DQA Policy (D-042)**\n\n"
            f"{blocking_reasons[0]}\n\n"
            "Final summary workbooks and modular ZIP packages cannot be downloaded until source data is corrected, "
            "or an authorized supervisor logs an override on the **Data Quality** page.",
            icon="🚫",
        )
        st.info(
            "💡 **Facility Remediation Access:** You may still download the **DQA Exceptions Workbook** "
            "and **Cleaning Log** below to identify and correct erroneous records.",
        )
    elif is_prov:
        st.warning(
            "⚠️ **PROVISIONAL Report Output:**\n\n"
            "This package contains Critical DQA exceptions that were authorized via supervisory override. "
            "All exported sheets and metadata are stamped with `PROVISIONAL`.",
            icon="⚠️",
        )
    else:
        st.success(
            "✅ **All Quality Gates Cleared:** 0 Critical DQA exceptions. Reporting packages are fully validated.",
            icon="✅",
        )

    # 3. Download Options (Decision D-043)
    st.subheader("1. Primary Export Packages")

    master_path = result.package_paths.get("master_workbook")
    zip_path = result.package_paths.get("zip_package")

    col_master, col_zip = st.columns(2)

    with col_master:
        if master_path and master_path.exists():
            with open(master_path, "rb") as f:
                master_bytes = f.read()

            st.download_button(
                label="📘 Download Master Excel Package (.xlsx)",
                data=master_bytes,
                file_name=master_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=is_blocked,
                type="primary",
                use_container_width=True,
                help="Consolidated all-in-one reporting package containing Summary, Cleaned Cohort, Cleaned KPLHIV, DQA Exceptions, Run Metadata, and Cleaning Log.",
            )
        else:
            st.button(
                "📘 Master Excel Package Unavailable", disabled=True, use_container_width=True
            )

    with col_zip:
        if zip_path and zip_path.exists():
            with open(zip_path, "rb") as f:
                zip_bytes = f.read()

            st.download_button(
                label="🗜️ Download Modular ZIP Archive (.zip)",
                data=zip_bytes,
                file_name=zip_path.name,
                mime="application/zip",
                disabled=is_blocked,
                type="secondary",
                use_container_width=True,
                help="ZIP archive containing individual standalone workbooks for each reporting module.",
            )
        else:
            st.button("🗜️ Modular ZIP Archive Unavailable", disabled=True, use_container_width=True)

    st.divider()

    # 4. Individual Component Downloads (Always available for DQA / Remediation)
    st.subheader("2. Individual Component Downloads")
    st.caption("Individual workbooks and audit trails for targeted facility review.")

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    # Cleaned Register
    with c1:
        st.markdown("**Cleaned Cohort Register**")
        if not is_blocked and master_path and master_path.exists():
            st.download_button(
                label="Download Cleaned Register (.xlsx)",
                data=master_bytes,
                file_name=f"Cleaned_Register_{result.population}_{result.period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_clean_reg",
                use_container_width=True,
            )
        else:
            st.button(
                "Cleaned Register (Gated)",
                disabled=True,
                key="btn_clean_reg_dis",
                use_container_width=True,
            )

    # Cleaned KPLHIV
    with c2:
        st.markdown("**Cleaned KPLHIV Tracking**")
        if not is_blocked and master_path and master_path.exists():
            st.download_button(
                label="Download Cleaned KPLHIV (.xlsx)",
                data=master_bytes,
                file_name=f"Cleaned_KPLHIV_{result.population}_{result.period_mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_clean_kp",
                use_container_width=True,
            )
        else:
            st.button(
                "Cleaned KPLHIV (Gated)",
                disabled=True,
                key="btn_clean_kp_dis",
                use_container_width=True,
            )

    # DQA Exceptions (ALWAYS AVAILABLE PER D-042)
    with c3:
        st.markdown("**DQA Exceptions Workbook** *(Always Available)*")
        dqa_file = (
            Path("runtime/temporary")
            / f"dqa_exceptions_{result.population}_{result.period_mode}.xlsx"
        )
        if dqa_file.exists():
            with open(dqa_file, "rb") as f:
                dqa_bytes = f.read()
            st.download_button(
                label="Download DQA Exceptions (.xlsx) 📥",
                data=dqa_bytes,
                file_name=f"DQA_Exceptions_{result.population}_{result.period_mode}.xlsx",
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

    # Audit & Reconciliation Log
    with c4:
        st.markdown("**Audit & Reconciliation Trail** *(Always Available)*")
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


render_exports()
