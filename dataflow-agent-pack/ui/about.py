"""DATAFLOW About Page.

Implements Master Brief §11:
- System information, version DATAFLOW v1.0.0, architecture overview, and confidentiality notices.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

import streamlit as st

from ui.session import render_access_guard


def render_about() -> None:
    st.title("ℹ️ About DATAFLOW")
    st.caption("Automated Key Population Data Management, Quality Assurance & Reporting System")

    if not render_access_guard("About"):
        return

    st.markdown(
        """
        ### DATAFLOW v1.0.2
        **DATAFLOW** is an automated, local, privacy-preserving data management and analytical pipeline
        engineered to convert Kenyan Key Population cohort registers (FSW, MSM, PWID, TG, VP) and KPLHIV workbooks
        into verified data structures, DQA exception workbooks, and standardized multi-tab Excel reporting packages.
        """
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🚀 Core Capabilities")
        st.markdown(
            """
            - **Multi-Population Ingestion:** Ingests complex multi-header Excel (`.xlsx`, `.xls`, `.xlsb`) registers.
            - **Vectorized Cleaning:** Standardizes phone numbers, dates, viral load titles, and missing geography.
            - **19-Rule DQA Engine:** Evaluates demographic and clinical rules (Duplicate UIC, Negative on ART, etc.).
            - **Analytical Engine:** Calculates all 48 Global Fund indicators and KPLHIV cascade metrics.
            - **Excel Reporting Exporter:** Produces formatted workbooks with dynamic `=SUM()` formulas, Cascadia Code headers, Candara body, and freeze panes.
            """
        )

    with col2:
        st.markdown("#### 🛡️ Privacy & Security Standards")
        st.markdown(
            """
            - **100% Local Execution:** Bound strictly to `127.0.0.1:8501` with telemetry disabled.
            - **Zero Identifier Leakage:** No client UICs, names, or phone numbers in logs, tracebacks, or metadata.
            - **Deterministic Masking:** Optional `MASK-XXXX` salted pseudo-hashing preserving cross-sheet linkage.
            - **Supervisory Override Audit:** Immutable append-only audit trail in `runtime/audit/override_log.jsonl`.
            - **Clean Session Hygiene:** All temporary working files purged on session reset.
            """
        )

    st.divider()

    st.warning(
        """
        **CONFIDENTIAL HEALTH DATA NOTICE:**
        This system processes sensitive Key Population health records subject to the **Kenya Data Protection Act 2019**
        and the **National AIDS & STI Control Programme (NASCOP)** data governance guidelines.
        Exported unmasked packages must never be transmitted over unsecured channels or shared with unauthorized entities.
        """,
        icon="⚠️",
    )

    with st.expander("💻 System Runtime Environment", expanded=False):
        st.write(f"• **Python Version:** `{sys.version}`")
        st.write(f"• **Streamlit Version:** `{st.__version__}`")
        st.write(
            f"• **Operating System:** `{platform.system()} {platform.release()} ({platform.machine()})`"
        )
        st.write("• **Network Binding:** `127.0.0.1:8501 (Localhost Only)`")
        st.write("• **Telemetry / Usage Stats:** `Disabled (gatherUsageStats = false)`")

    st.divider()
    st.subheader("🩺 Diagnostic Support Bundle")
    st.caption(
        "Generate a sanitized diagnostic ZIP archive containing environment specs, configuration hashes, "
        "and redacted logs (with zero client identifiers or PII) for technical assistance."
    )
    from core.diagnostics import build_diagnostic_bundle

    if st.button("Generate Diagnostic Support Bundle 📦", use_container_width=True):
        bundle_path = build_diagnostic_bundle()
        st.session_state["diag_bundle_path"] = str(bundle_path)
        st.success(f"Diagnostic bundle generated: `{bundle_path.name}`")

    bundle_path_str = st.session_state.get("diag_bundle_path")
    if bundle_path_str and Path(bundle_path_str).exists():
        with open(bundle_path_str, "rb") as bf:
            bbytes = bf.read()
        st.download_button(
            label="Download Diagnostic Support Bundle (.zip) 📥",
            data=bbytes,
            file_name=Path(bundle_path_str).name,
            mime="application/zip",
            use_container_width=True,
        )


render_about()
