"""DATAFLOW Upload Page.

Handles cohort workbook ingestion, validation, population/period selection, and state transition.
Implements:
- Sabotage handling with friendly, data-free messages (wrong format, corrupt file, missing sheet).
- SHA-256 hash calculation for reproducibility and caching.
- State progression to 'UPLOADED'.
"""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import streamlit as st

from core.runner import compute_file_hash
from core.workflow_manager import WorkflowStage
from ui.session import advance_workflow_stage, render_access_guard

VALID_EXTENSIONS = {".xlsx", ".xls", ".xlsb", ".csv"}
POPULATIONS = ["FSW", "MSM", "PWID", "TG", "VP"]
PERIOD_MODES = ["SEM", "Q1", "Q2"]


def detect_population_from_name(filename: str) -> str:
    """Heuristic population detection from filename; defaults to FSW."""
    name_upper = filename.upper()
    for pop in ["PWID", "MSM", "TG", "VP", "FSW"]:
        if pop in name_upper:
            return pop
    return "FSW"


def validate_uploaded_bytes(
    file_bytes: bytes, file_name: str, population: str
) -> tuple[bool, str | None]:
    """
    Validates uploaded file structure without exposing client identifiers.
    Returns (is_valid, error_message).
    """
    ext = Path(file_name).suffix.lower()
    if ext not in VALID_EXTENSIONS:
        return (
            False,
            f"Unsupported file extension '{ext}'. Please upload an Excel workbook (.xlsx, .xls, .xlsb) or CSV.",
        )

    if len(file_bytes) == 0:
        return False, "The uploaded file is empty (0 bytes). Please upload a valid cohort workbook."

    # For Excel workbooks, inspect sheet structure
    if ext in [".xlsx", ".xlsm", ".xlsb", ".xls"]:
        sheetnames: list[str] = []

        # 1. Try Calamine (fast, native xlsx/xlsb/xls support)
        try:
            from python_calamine import CalamineWorkbook

            wb_c = CalamineWorkbook.from_filelike(io.BytesIO(file_bytes))
            sheetnames = wb_c.sheet_names
        except Exception:
            pass

        # 2. Try openpyxl if .xlsx/.xlsm and calamine failed
        if not sheetnames and ext in [".xlsx", ".xlsm"]:
            try:
                wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
                sheetnames = wb.sheetnames
                wb.close()
            except Exception:
                pass

        # If neither loader could parse any sheets, the workbook is corrupt or unreadable
        if not sheetnames:
            return (
                False,
                "The uploaded Excel workbook appears to be corrupt or malformed and could not be parsed.",
            )

        # Check for at least one sheet containing Register or Cohort
        reg_found = any(
            "REG" in s.upper() or "COHORT" in s.upper() or population.upper() in s.upper()
            for s in sheetnames
        )
        if not reg_found and len(sheetnames) == 1:
            # Single sheet workbook is accepted as register
            reg_found = True

        if not reg_found:
            return (
                False,
                f"Required register sheet not found. Workbook contains: {sheetnames}. "
                "Expected a sheet named 'Register' or matching the target population.",
            )

    return True, None


def render_upload() -> None:
    st.title("📁 Upload Cohort Data")
    st.caption(
        "Upload Key Population cohort registers and KPLHIV tracking workbooks for processing."
    )

    # Guard check
    if not render_access_guard("Upload Data"):
        return

    with st.container():
        st.subheader("1. Cohort File Selection")
        uploaded_file = st.file_uploader(
            label="Upload Register Workbook (.xlsx, .xls, .xlsb, .csv)",
            type=["xlsx", "xls", "xlsb", "csv"],
            help="Upload the cohort register workbook containing client encounters and KPLHIV tracking records.",
        )

        col_pop, col_per = st.columns(2)

        with col_pop:
            default_pop = (
                detect_population_from_name(uploaded_file.name) if uploaded_file else "FSW"
            )
            pop_index = POPULATIONS.index(default_pop) if default_pop in POPULATIONS else 0
            population = st.selectbox(
                "Target Key Population",
                options=POPULATIONS,
                index=pop_index,
                help="Select the key population cohort register type.",
            )

        with col_per:
            period_mode = st.selectbox(
                "Reporting Period Mode",
                options=PERIOD_MODES,
                index=0,
                help="Select Semi-Annual (SEM) full reporting or quarterly (Q1/Q2) summary mode.",
            )

        st.subheader("2. Quality & Privacy Options")
        col_crit, col_mask = st.columns(2)
        with col_crit:
            block_on_crit = st.checkbox(
                "Strict DQA Gating (Flag Critical exceptions as PROVISIONAL)",
                value=st.session_state.get("block_on_critical", False),
                help="When enabled, requires supervisory override before final approval. All exports remain downloadable with advisory notice.",
            )
            st.session_state["block_on_critical"] = block_on_crit

        with col_mask:
            mask_ident = st.checkbox(
                "Mask client identifiers (UIC/CCC) in exports",
                value=st.session_state.get("mask_identifiers", False),
                help="Enforces Decision D-035: replaces raw UIC and CCC numbers with salted hash MASK-XXXX.",
            )
            st.session_state["mask_identifiers"] = mask_ident

        st.divider()

        # Handle file upload processing
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            file_name = uploaded_file.name
            file_hash = compute_file_hash(file_bytes)

            is_valid, err_msg = validate_uploaded_bytes(file_bytes, file_name, population)

            if not is_valid:
                st.session_state["stage"] = "ERROR"
                st.session_state["error_message"] = err_msg
                st.error(f"❌ **Validation Failed:** {err_msg}", icon="❌")
                return

            # Update session state with valid upload
            st.session_state["uploaded_file_name"] = file_name
            st.session_state["uploaded_file_hash"] = file_hash
            st.session_state["uploaded_file_bytes"] = file_bytes
            st.session_state["population"] = population
            st.session_state["period_mode"] = period_mode
            advance_workflow_stage(WorkflowStage.UPLOADED)
            st.session_state["error_message"] = None

            # Pre-Processing Template Concordance Audit
            from core.template_validator import validate_kp_template_concordance

            temp_dir = Path("runtime/temporary")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"upload_{file_hash[:10]}_{file_name}"
            temp_path.write_bytes(file_bytes)

            template_report = validate_kp_template_concordance(temp_path)
            if not template_report.is_valid:
                st.session_state["stage"] = "ERROR"
                st.session_state["error_message"] = "; ".join(template_report.errors)
                st.error(
                    "❌ **Template Concordance Error:**\n\n"
                    + "\n".join(f"- {e}" for e in template_report.errors)
                )
                return

            st.success(
                f"✅ **File Validated Successfully!**\n\n"
                f"• **Filename:** `{file_name}` ({len(file_bytes):,} bytes)\n\n"
                f"• **SHA-256 Hash:** `{file_hash}`\n\n"
                f"• **Target Population:** `{population}` | **Period:** `{period_mode}`",
                icon="✅",
            )

            with st.expander("📋 Pre-Processing Template Concordance Audit", expanded=True):
                st.markdown(template_report.summary_markdown())

            if st.button("🚀 Proceed to Processing", type="primary", use_container_width=True):
                advance_workflow_stage(WorkflowStage.PROCESSING)
                st.switch_page("ui/processing.py")


render_upload()
