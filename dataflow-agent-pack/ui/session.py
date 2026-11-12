"""Session State Machine and Temporary Storage Management.

Implements:
- Decisions D-041 (Guided State Machine)
- Decision D-044 (Complete Purge on New Session and storage hygiene)
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import streamlit as st

from core.override import OverrideManager

TEMP_DIR = Path("runtime/temporary")
AUDIT_LOG_PATH = Path("runtime/audit/override_log.jsonl")


def purge_temporary_storage(target_dir: Path | str = TEMP_DIR) -> int:
    """
    Safely deletes all files and directories inside runtime/temporary/.
    Preserves the directory itself. Returns the count of deleted items.
    """
    path = Path(target_dir)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return 0

    deleted_count = 0
    for item in path.iterdir():
        if item.name == ".gitkeep":
            continue
        try:
            if item.is_file() or item.is_symlink():
                item.unlink(missing_ok=True)
                deleted_count += 1
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                deleted_count += 1
        except Exception:
            pass
    return deleted_count


def init_session_state() -> None:
    """Initializes standard session state keys if not already present."""
    defaults: dict[str, Any] = {
        "stage": "IDLE",  # IDLE -> UPLOADED -> PROCESSING -> PROCESSED -> ERROR
        "uploaded_file_name": "",
        "uploaded_file_hash": "",
        "uploaded_file_bytes": None,
        "population": "FSW",
        "period_mode": "SEM",
        "block_on_critical": False,
        "mask_identifiers": False,
        "pipeline_result": None,
        "stage_timings": {},
        "error_message": None,
        "error_details": None,
        "override_manager": None,
        "active_page": "Dashboard",
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if st.session_state["override_manager"] is None:
        st.session_state["override_manager"] = OverrideManager(audit_log_path=AUDIT_LOG_PATH)


def reset_session() -> None:
    """
    Implements Decision D-044:
    Wipes session state and completely deletes files in runtime/temporary/.
    """
    purge_temporary_storage()

    st.session_state["stage"] = "IDLE"
    st.session_state["uploaded_file_name"] = ""
    st.session_state["uploaded_file_hash"] = ""
    st.session_state["uploaded_file_bytes"] = None
    st.session_state["population"] = "FSW"
    st.session_state["period_mode"] = "SEM"
    st.session_state["block_on_critical"] = True
    st.session_state["mask_identifiers"] = False
    st.session_state["pipeline_result"] = None
    st.session_state["stage_timings"] = {}
    st.session_state["error_message"] = None
    st.session_state["error_details"] = None

    if st.session_state.get("override_manager") is not None:
        st.session_state["override_manager"].clear()


def check_page_access(page_name: str) -> bool:
    """
    Enforces Decision D-041 (Guided state machine):
    - IDLE: Only Dashboard, Upload Data, Configuration, About accessible.
    - UPLOADED: Upload Data and Processing unlocked.
    - PROCESSED: All pages (Data Quality, Analytics, Export Reports) unlocked.
    """
    stage = st.session_state.get("stage", "IDLE")

    always_accessible = {"Dashboard", "Upload Data", "Configuration", "About"}
    if page_name in always_accessible:
        return True

    if page_name == "Processing":
        return stage in ("UPLOADED", "PROCESSING", "PROCESSED")

    downstream_pages = {"Data Quality", "Analytics", "Export Reports"}
    if page_name in downstream_pages:
        return stage == "PROCESSED"

    return True


def render_access_guard(page_name: str) -> bool:
    """
    Displays an informational banner if the page is locked, returning False.
    Returns True if accessible.
    """
    if check_page_access(page_name):
        return True

    stage = st.session_state.get("stage", "IDLE")
    st.warning(
        f"**Page Locked:** The **{page_name}** page requires pipeline processing to complete first.",
        icon="🔒",
    )

    if stage == "IDLE":
        st.info(
            "👉 Please go to **Upload Data** in the sidebar to upload a cohort register workbook."
        )
    elif stage == "UPLOADED":
        st.info(
            "👉 Please navigate to **Processing** in the sidebar to run the validation pipeline."
        )
    elif stage == "ERROR":
        st.error(
            "⚠️ The last processing run encountered an error. Please re-check the file on the Upload page."
        )

    return False
