"""DATAFLOW Upload Page — Cohort Register Ingestion & Pre-Flight Validation.

Primary Audience: Monitoring & Evaluation (M&E) Specialists, Data Officers, Lead Analysts.
Primary Question: "Is this workbook structurally sound, does it match approved DataFlow templates, and is it ready for automated processing?"

Strictly adheres to Master Brief §3, §4, §5 and Decisions D-040/D-041:
- Scoped presentation design system mirroring Dashboard and Analytics (keyed containers, cards, hover lift).
- Actionable, non-technical pre-flight validation reporting with downloadable audit artifacts.
- Deterministic SHA-256 file hashing and session state synchronization.
- Seamless sequential progression to Stage 1–5 processing.
"""

from __future__ import annotations

import html
import io
import re
import sys
from pathlib import Path

# Ensure project root takes precedence in sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] != _ROOT:
    if _ROOT in sys.path:
        sys.path.remove(_ROOT)
    sys.path.insert(0, _ROOT)

import openpyxl  # noqa: E402
import streamlit as st  # noqa: E402

from core.runner import compute_file_hash  # noqa: E402
from core.template_validator import validate_kp_template_concordance  # noqa: E402
from core.workflow_manager import WorkflowStage  # noqa: E402
from ui.session import advance_workflow_stage, render_access_guard  # noqa: E402

VALID_EXTENSIONS = {".xlsx", ".xls", ".xlsb", ".csv"}
POPULATIONS = ["FSW", "MSM", "PWID", "TG", "VP"]
PERIOD_MODES = ["SEM", "Q1", "Q2"]
POPULATION_CHOICES = ["Select Population Type", "FSW", "MSM", "PWID", "TG", "VP"]
PERIOD_CHOICES = ["Select Period", "SEM", "Q1", "Q2"]


# =============================================================================
# PRESENTATION DESIGN SYSTEM (display-only: scoped CSS, cards, hero, badges)
# =============================================================================
_ACCENT_BLUE = "#3B82F6"
_ACCENT_VIOLET = "#8B5CF6"
_ACCENT_TEAL = "#14B8A6"
_ACCENT_GREEN = "#22C55E"
_ACCENT_AMBER = "#F59E0B"
_ACCENT_RED = "#EF4444"

_UPLOAD_CSS = """
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
.dfx-hero.error {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.16), rgba(245, 158, 11, 0.12));
    border-color: rgba(239, 68, 68, 0.35);
}
.dfx-hero.success {
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
.dfx-badge.active {
    background: rgba(34, 197, 94, 0.15);
    border-color: rgba(34, 197, 94, 0.45);
}

/* ---- guidance cards ---- */
.dfx-guidance-card {
    background: rgba(128, 128, 128, 0.06);
    border: 1px solid rgba(128, 128, 128, 0.20);
    border-radius: 14px;
    padding: 16px 18px;
    height: 100%;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
.dfx-guidance-card .card-title {
    font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;
}
.dfx-guidance-card .card-body {
    font-size: 0.83rem; opacity: 0.85; line-height: 1.45;
}

/* ---- pre-flight metric cards ---- */
.st-key-audit_cards [data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.07);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-left: 6px solid #3B82F6;
    border-radius: 14px;
    padding: 16px 20px 14px 20px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.st-key-audit_cards [data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
}
.st-key-audit_cards [data-testid="stMetricLabel"] p {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.75;
}
.st-key-audit_cards [data-testid="stMetricValue"] {
    font-size: 2.0rem;
    font-weight: 700;
    line-height: 1.15;
}
.st-key-audit_cards [data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] { border-left-color: #3B82F6; }
.st-key-audit_cards [data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { border-left-color: #8B5CF6; }
.st-key-audit_cards [data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { border-left-color: #22C55E; }

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


def _format_size(num_bytes: int) -> str:
    """Formats byte counts cleanly (KB or MB)."""
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def detect_population_from_name(filename: str) -> str:
    """Heuristic population detection from filename using token matching; returns UNKNOWN if undetected."""
    name_upper = filename.upper()
    for pop in ["PWID", "MSM", "TG", "VP", "FSW"]:
        if re.search(rf"(?:^|[\s_\-.\(\)\[\]]){pop}(?:$|[\s_\-.\(\)\[\]])", name_upper):
            return pop
    return "UNKNOWN"


def detect_population_from_content(file_bytes: bytes, ext: str) -> str:
    """Inspects Register sheet header/rows for typology type column values."""
    if ext in [".xlsx", ".xlsb", ".xls", ".xlsm"]:
        try:
            from python_calamine import CalamineWorkbook

            wb = CalamineWorkbook.from_filelike(io.BytesIO(file_bytes))
            for s in wb.sheet_names:
                if any(x in s.upper() for x in ["REGISTER", "REG"]):
                    rows = wb.get_sheet_by_name(s).to_python()
                    for r_idx in range(min(5, len(rows))):
                        row = rows[r_idx]
                        for c_idx, cell in enumerate(row):
                            c_str = str(cell).strip().lower()
                            if any(k in c_str for k in ["key/vulnerable population", "typology", "population type"]):
                                for data_r in rows[r_idx + 1 : r_idx + 20]:
                                    if len(data_r) > c_idx and data_r[c_idx]:
                                        val = str(data_r[c_idx]).strip().upper()
                                        if val in POPULATIONS:
                                            return val
        except Exception:
            pass
    return "UNKNOWN"


def validate_uploaded_bytes(
    file_bytes: bytes, file_name: str, population: str
) -> tuple[bool, str | None]:
    """Validates uploaded file structure without exposing client identifiers.

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

        if not sheetnames:
            return (
                False,
                "The uploaded Excel workbook appears to be corrupt or malformed and could not be parsed.",
            )

        # Check for at least one sheet containing Register
        reg_found = any(
            "REGISTER" in s.upper() or "REG" in s.upper() or population.upper() in s.upper()
            for s in sheetnames
        )
        if not reg_found and len(sheetnames) == 1:
            # Single sheet workbook is accepted as register
            reg_found = True

        if not reg_found:
            return (
                False,
                f"Required register sheet not found. Workbook contains: {sheetnames}. "
                "Expected a worksheet named 'Register' or matching the target population.",
            )

    return True, None


def render_upload() -> None:
    st.title("📁 Upload Cohort Data")
    st.caption("Workbook Ingestion & Pre-Flight Validation — Ingest and verify Key Population registers before processing.")

    # Guard check
    if not render_access_guard("Upload Data"):
        return

    # Inject Scoped Presentation Stylesheet
    st.markdown(_UPLOAD_CSS, unsafe_allow_html=True)

    # 1. Hero Header Banner
    st.markdown(
        """
        <div class="dfx-hero">
            <div>
                <div class="title">Cohort Register Ingestion & Pre-Flight Validation</div>
                <div class="sub">Automated template structure inspection, worksheet verification, and typology concordance.</div>
            </div>
            <div class="pills">
                <span class="dfx-pill ok">🛡️ Pre-Flight Verification</span>
                <span class="dfx-pill info">🔒 100% Localhost / Offline</span>
                <span class="dfx-pill info">⚡ Calamine Acceleration</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Guidance Checklist Cards (Visible before and during file selection)
    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        st.markdown(
            """
            <div class="dfx-guidance-card">
                <div class="card-title">📑 1. Required Worksheets</div>
                <div class="card-body">
                    Must strictly contain <b>Register</b> (client encounters) and <b>KPLHIV</b> (clinical tracking) sheets.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g_col2:
        st.markdown(
            """
            <div class="dfx-guidance-card">
                <div class="card-title">⚡ 2. Supported Formats</div>
                <div class="card-body">
                    Supports <b>.xlsx</b>, <b>.xlsb</b> (recommended for &gt;10k rows), <b>.xls</b>, and <b>.csv</b> formats.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g_col3:
        st.markdown(
            """
            <div class="dfx-guidance-card">
                <div class="card-title">🛡️ 3. Privacy & Integrity</div>
                <div class="card-body">
                    Deterministic SHA-256 fingerprinting. Client identifiers (UIC/CCC) can be salted and masked on export.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Parameters & File Ingestion Section
    with st.container(border=True):
        st.markdown("#### ⚙️ 1. Target Cohort Configuration & Parameters")

        # Ensure fresh default state: initialize to placeholders if not set
        if st.session_state.get("sel_target_population") not in POPULATION_CHOICES:
            st.session_state["sel_target_population"] = "Select Population Type"

        if st.session_state.get("sel_reporting_period") not in PERIOD_CHOICES:
            st.session_state["sel_reporting_period"] = "Select Period"

        # Determine currently selected population and period mode from session state
        current_pop = st.session_state.get("population") or st.session_state.get("sel_target_population")
        pop_index = POPULATION_CHOICES.index(current_pop) if current_pop in POPULATION_CHOICES else 0

        current_per = st.session_state.get("period_mode") or st.session_state.get("sel_reporting_period")
        per_index = PERIOD_CHOICES.index(current_per) if current_per in PERIOD_CHOICES else 0

        col_pop, col_per = st.columns(2)
        with col_pop:
            selected_pop = st.selectbox(
                "Target Key Population *",
                options=POPULATION_CHOICES,
                index=pop_index,
                help="Mandatory: Select the key population cohort register typology (FSW, MSM, PWID, TG, VP) before uploading.",
                key="sel_target_population",
            )
        with col_per:
            selected_per = st.selectbox(
                "Reporting Period Mode *",
                options=PERIOD_CHOICES,
                index=per_index,
                help="Mandatory: Select Semi-Annual (SEM) full reporting or quarterly (Q1/Q2) summary mode before uploading.",
                key="sel_reporting_period",
            )

        # Update session state with explicitly chosen values only
        if selected_pop in POPULATIONS:
            st.session_state["population"] = selected_pop
            st.session_state["population_explicitly_selected"] = True
            population = selected_pop
        else:
            st.session_state["population"] = None
            st.session_state["population_explicitly_selected"] = False
            population = None

        if selected_per in PERIOD_MODES:
            st.session_state["period_mode"] = selected_per
            st.session_state["period_explicitly_selected"] = True
            period_mode = selected_per
        else:
            st.session_state["period_mode"] = None
            st.session_state["period_explicitly_selected"] = False
            period_mode = None

        is_configured = bool(population and period_mode)

        st.markdown("##### 🔒 Quality & Privacy Options")
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

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. File Dropzone Section
    with st.container(border=True):
        st.markdown("#### 📂 2. Cohort Register File Upload")
        st.caption("Upload the cohort register workbook containing client encounters and KPLHIV tracking records.")

        if not is_configured:
            st.warning(
                "🔒 **Upload Locked — Population & Period Selection Required**\n\n"
                "Please select both a **Target Key Population** and a **Reporting Period Mode** in Section 1 above to reveal the cohort file upload area.",
                icon="🔒",
            )
            uploaded_file = None
        else:
            st.success(
                f"🔓 **Upload Unlocked:** Ready to accept **{population}** cohort register for **{period_mode}** reporting period.",
                icon="🔓",
            )

            uploaded_file = st.file_uploader(
                label="Upload Register Workbook (.xlsx, .xls, .xlsb, .csv)",
                type=["xlsx", "xls", "xlsb", "csv"],
                help="Select the Excel workbook conforming to the Kenya KP Data Standard template.",
                label_visibility="collapsed",
                key="cohort_file_uploader",
            )

    # 5. Handle file upload & validation execution
    if uploaded_file is not None and is_configured:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name
        file_hash = compute_file_hash(file_bytes)
        ext = Path(file_name).suffix.lower()

        # Typology mismatch advisory check
        detected_pop = detect_population_from_name(file_name)
        if detected_pop == "UNKNOWN":
            detected_pop = detect_population_from_content(file_bytes, ext)
        if detected_pop != "UNKNOWN" and detected_pop != population:
            st.warning(
                f"⚠️ **Typology Mismatch Detected:** You selected **{population}**, but the uploaded file appears to be **{detected_pop}** (`{file_name}`). "
                f"If this is unintentional, update the Target Key Population dropdown in Section 1 to **{detected_pop}**.",
                icon="⚠️",
            )

        # Basic format & emptiness checks
        if ext not in VALID_EXTENSIONS:
            st.session_state["stage"] = "ERROR"
            err_msg = f"Unsupported file extension '{ext}'. Please upload an Excel workbook (.xlsx, .xls, .xlsb) or CSV."
            st.session_state["error_message"] = err_msg
            st.error(f"❌ **Validation Failed:** {err_msg}", icon="❌")
            return

        if len(file_bytes) == 0:
            st.session_state["stage"] = "ERROR"
            err_msg = "The uploaded file is empty (0 bytes). Please upload a valid cohort workbook."
            st.session_state["error_message"] = err_msg
            st.error(f"❌ **Validation Failed:** {err_msg}", icon="❌")
            return

        # Save uploaded bytes to temporary session storage
        temp_dir = Path("runtime/temporary")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"upload_{file_hash[:10]}_{file_name}"
        temp_path.write_bytes(file_bytes)

        # Centralized Workbook & Template Concordance Validation
        template_report = validate_kp_template_concordance(temp_path, population=population)

        # Update session state with valid metadata
        st.session_state["uploaded_file_name"] = file_name
        st.session_state["uploaded_file_hash"] = file_hash
        st.session_state["uploaded_file_bytes"] = file_bytes
        st.session_state["population"] = population
        st.session_state["period_mode"] = period_mode

        val_df = template_report.to_dataframe()

        # Handle validation failures
        if not template_report.is_valid:
            st.session_state["stage"] = "ERROR"
            st.session_state["error_message"] = "; ".join(template_report.errors)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="dfx-hero error">
                    <div>
                        <div class="title">❌ Pre-Flight Workbook Validation Blocked</div>
                        <div class="sub">The uploaded workbook does not match mandatory template requirements.</div>
                    </div>
                    <div class="pills">
                        <span class="dfx-pill bad">🔴 {len(template_report.errors)} Structural Errors</span>
                        <span class="dfx-pill warn">⚠️ Action Required</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Actionable non-technical error markdown
            st.error(template_report.actionable_error_markdown(), icon="❌")

            # Expandable validation issues report table
            with st.expander("📋 Pre-Flight Workbook Validation Report (Validation Issues Detected)", expanded=True):
                st.caption("Review discrete structural validation checks below. All 'Failed' items must be resolved in Excel before processing.")
                st.dataframe(val_df, use_container_width=True, hide_index=True)

                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.download_button(
                        label="📥 Download Validation Report (CSV)",
                        data=template_report.to_csv_bytes(),
                        file_name=f"Validation_Report_{population}_{file_name}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with d_col2:
                    st.download_button(
                        label="📥 Download Validation Report (Excel)",
                        data=template_report.to_excel_bytes(),
                        file_name=f"Validation_Report_{population}_{file_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

            # Technical developer diagnostics
            with st.expander("🛠️ Technical Diagnostic Details (for Developers)", expanded=False):
                st.json({
                    "filename": file_name,
                    "file_size_bytes": len(file_bytes),
                    "sha256": file_hash,
                    "detected_format": template_report.detected_format,
                    "detected_sheets": template_report.detected_sheets,
                    "errors": template_report.errors,
                    "warnings": template_report.warnings,
                    "missing_core_columns": template_report.missing_core_columns,
                })

            st.warning("⚠️ **Processing is blocked** until mandatory structural validation checks pass. Please correct your workbook and re-upload.")
            return

        # When workbook validation passes successfully
        advance_workflow_stage(WorkflowStage.UPLOADED)
        st.session_state["error_message"] = None

        # Reset pipeline execution state for uploaded cohort so user can run it fresh on processing page
        st.session_state["pipeline_result"] = None
        st.session_state["stage_timings"] = {}
        st.session_state["overall_progress"] = 0.0
        st.session_state["activity_logs"] = []

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Success Hero Banner
        st.markdown(
            f"""
            <div class="dfx-hero success">
                <div>
                    <div class="title">✅ Pre-Flight Validation Passed Successfully</div>
                    <div class="sub">
                        📄 <b>{_esc(file_name)}</b> &nbsp;·&nbsp; 👥 <b>{_esc(population)}</b> &nbsp;·&nbsp; 🗓️ <b>{_esc(period_mode)}</b>
                    </div>
                </div>
                <div class="pills">
                    <span class="dfx-pill ok">🛡️ All Mandatory Checks Passed</span>
                    <span class="dfx-pill info">⚡ {_format_size(len(file_bytes))}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Context Badges
        st.markdown(
            f"""
            <div class="dfx-badges">
                <span class="dfx-badge active">👥 Typology: {_esc(population)}</span>
                <span class="dfx-badge active">🗓️ Period: {_esc(period_mode)}</span>
                <span class="dfx-badge">🔑 SHA-256: {_esc(file_hash[:16])}...</span>
                <span class="dfx-badge">📋 Layout: {_esc(template_report.detected_format)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 6. Pre-Flight Audit KPI Metric Cards (Claude's presentation card system)
        with _section_container("audit_cards"):
            m1, m2, m3 = st.columns(3)
            m1.metric(
                label="Workbook Size & Format",
                value=_format_size(len(file_bytes)),
                delta=ext.upper().replace(".", ""),
                help="Uploaded file payload size and detected binary/xml format.",
            )
            sheets_count = len(template_report.detected_sheets)
            m2.metric(
                label="Detected Worksheets",
                value=f"{sheets_count} Sheets",
                delta="Register & KPLHIV" if "KPLHIV" in template_report.detected_sheets else "Register Only",
                delta_color="normal",
                help="Worksheets detected conforming to KP reporting template specifications.",
            )
            pass_count = sum(1 for item in template_report.items if item.status == "Passed")
            total_checks = len(template_report.items)
            m3.metric(
                label="Pre-Flight Health",
                value=f"{pass_count}/{total_checks} Checks",
                delta="100% Passed",
                delta_color="normal",
                help="Discrete pre-flight structural checks evaluated on this workbook.",
            )

        # 7. Collapsible Pre-Flight Validation Report Table (Collapsed when passed)
        with st.expander("📋 Pre-Flight Workbook Validation Report (All Mandatory Checks Passed)", expanded=False):
            st.caption("Discrete structural validation audit results. All mandatory checks have succeeded.")
            st.dataframe(val_df, use_container_width=True, hide_index=True)

            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.download_button(
                    label="📥 Download Validation Report (CSV)",
                    data=template_report.to_csv_bytes(),
                    file_name=f"Validation_Report_{population}_{file_name}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with d_col2:
                st.download_button(
                    label="📥 Download Validation Report (Excel)",
                    data=template_report.to_excel_bytes(),
                    file_name=f"Validation_Report_{population}_{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        # 8. Workflow Progression: Proceed to Processing Card
        with _section_container("next_section"):
            st.subheader("🏁 Next Workflow Step")
            st.caption("Your cohort register is structurally verified. Proceed to automated multi-stage processing.")

            col_inf, col_btn = st.columns([2, 1])
            with col_inf:
                st.info("ℹ️ Next Stage: Ingests register records, normalizes dates/geography, and assesses DQA exceptions.")
            with col_btn:
                if st.button("🚀 Proceed to Processing ➡️", type="primary", use_container_width=True):
                    advance_workflow_stage(WorkflowStage.UPLOADED)
                    st.switch_page("ui/processing.py")

    elif uploaded_file is not None and not is_configured:
        st.error(
            "❌ **Configuration Required:** Please select both **Target Key Population** and **Reporting Period Mode** in Section 1 above before uploading.",
            icon="❌",
        )


render_upload()
