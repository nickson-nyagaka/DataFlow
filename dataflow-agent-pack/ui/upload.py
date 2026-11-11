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
from ui.session import render_access_guard

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

    # For .xlsx files, inspect sheet structure with openpyxl read-only
    if ext == ".xlsx":
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            sheetnames = wb.sheetnames
            wb.close()

            # Check for at least one sheet containing Register or Cohort
            reg_found = any(
                "REG" in s.upper() or "COHORT" in s.upper() or population in s.upper()
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

        except Exception:
            return (
                False,
                "The uploaded Excel workbook appears to be corrupt or malformed and could not be parsed.",
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
                "Block report exports on Critical DQA exceptions",
                value=st.session_state.get("block_on_critical", True),
                help="Enforces Decision D-042: prevents export of analytical summaries if Critical data errors exist.",
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
            st.session_state["stage"] = "UPLOADED"
            st.session_state["error_message"] = None

            st.success(
                f"✅ **File Validated Successfully!**\n\n"
                f"• **Filename:** `{file_name}` ({len(file_bytes):,} bytes)\n\n"
                f"• **SHA-256 Hash:** `{file_hash}`\n\n"
                f"• **Target Population:** `{population}` | **Period:** `{period_mode}`",
                icon="✅",
            )

            if st.button("🚀 Proceed to Processing", type="primary", use_container_width=True):
                st.session_state["active_page"] = "Processing"
                st.rerun()


render_upload()
