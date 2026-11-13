"""Session State Machine and Temporary Storage Management for DATAFLOW.

Implements Master Brief §3, §4, §5, §18:
- Centralized WorkflowState machine integration.
- Deterministic session ID generation and isolation.
- Genuine New Session reset (purging memory, caches, temporary files).
- Centralized page access enforcement with automatic redirection.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

from core.override import OverrideManager
from core.workflow_manager import (
    PAGE_SCRIPT_PATHS,
    WorkflowStage,
    can_access_page,
    get_earliest_incomplete_page,
    get_required_preceding_stage,
    normalize_stage,
)

TEMP_DIR = Path("runtime/temporary")
AUDIT_LOG_PATH = Path("runtime/audit/override_log.jsonl")


def generate_session_id() -> str:
    """Generates a unique session identifier."""
    return f"SES_{uuid.uuid4().hex[:12].upper()}"


def purge_temporary_storage(target_dir: Path | str = TEMP_DIR) -> int:
    """Safely deletes all files and directories inside runtime/temporary/.

    Preserves the directory itself and .gitkeep. Returns the count of deleted items.
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
        "session_id": generate_session_id(),
        "workflow_stage": WorkflowStage.EMPTY,
        "stage": "IDLE",  # Kept for backward compatibility
        "uploaded_file_name": "",
        "uploaded_file_hash": "",
        "uploaded_file_bytes": None,
        "population": "FSW",
        "period_mode": "SEM",
        "block_on_critical": False,
        "mask_identifiers": False,
        "pipeline_result": None,
        "stage_timings": {},
        "progress_state": {},
        "dqa_reviewed": False,
        "dashboard_viewed": False,
        "analytics_viewed": False,
        "error_message": None,
        "error_details": None,
        "override_manager": None,
        "active_page": "Upload Data",
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if st.session_state["override_manager"] is None:
        st.session_state["override_manager"] = OverrideManager(audit_log_path=AUDIT_LOG_PATH)


def reset_session() -> None:
    """Performs a genuine application reset per Master Brief §18.

    - Clears uploaded dataset and byte buffers
    - Clears pipeline results and cached dataframes
    - Purges temporary upload and export files in runtime/temporary/
    - Generates a fresh unique session_id
    - Resets workflow_stage to EMPTY
    - Locks all downstream pages
    - Clears overrides and stage timings
    """
    purge_temporary_storage()

    # Invalidate runner in-memory cache if imported
    try:
        from core.runner import clear_pipeline_cache

        clear_pipeline_cache()
    except (ImportError, AttributeError):
        pass

    st.session_state["session_id"] = generate_session_id()
    st.session_state["workflow_stage"] = WorkflowStage.EMPTY
    st.session_state["stage"] = "IDLE"
    st.session_state["uploaded_file_name"] = ""
    st.session_state["uploaded_file_hash"] = ""
    st.session_state["uploaded_file_bytes"] = None
    st.session_state["population"] = "FSW"
    st.session_state["period_mode"] = "SEM"
    st.session_state["block_on_critical"] = False
    st.session_state["mask_identifiers"] = False
    st.session_state["pipeline_result"] = None
    st.session_state["stage_timings"] = {}
    st.session_state["progress_state"] = {}
    st.session_state["dqa_reviewed"] = False
    st.session_state["dashboard_viewed"] = False
    st.session_state["analytics_viewed"] = False
    st.session_state["error_message"] = None
    st.session_state["error_details"] = None
    st.session_state["active_page"] = "Upload Data"

    if st.session_state.get("override_manager") is not None:
        st.session_state["override_manager"].clear()


def get_current_workflow_stage() -> WorkflowStage:
    """Returns the active WorkflowStage enum."""
    raw = st.session_state.get("workflow_stage")
    if raw is None:
        # Fall back to legacy stage
        legacy = st.session_state.get("stage", "IDLE")
        raw = WorkflowStage.UPLOADED if legacy == "UPLOADED" else WorkflowStage.EMPTY
    return normalize_stage(raw)


def advance_workflow_stage(target_stage: WorkflowStage) -> None:
    """Safely updates workflow stage in session state."""
    st.session_state["workflow_stage"] = target_stage
    # Keep legacy stage synchronized
    if target_stage in (WorkflowStage.EMPTY,):
        st.session_state["stage"] = "IDLE"
    elif target_stage in (WorkflowStage.UPLOADED,):
        st.session_state["stage"] = "UPLOADED"
    elif target_stage in (WorkflowStage.PROCESSING,):
        st.session_state["stage"] = "PROCESSING"
    else:
        st.session_state["stage"] = "PROCESSED"


def check_page_access(page_name: str) -> bool:
    """Checks page access permissions against the centralized state machine."""
    current_stage = get_current_workflow_stage()
    return can_access_page(page_name, current_stage)


def render_access_guard(page_name: str) -> bool:
    """Enforces centralized page-access validation per Master Brief §5.

    If access is denied:
    1. Prevents protected page execution (returns False).
    2. Displays an explanatory warning with the required preceding stage.
    3. Provides a button redirecting to the earliest incomplete workflow stage.
    """
    if check_page_access(page_name):
        return True

    current_stage = get_current_workflow_stage()
    preceding = get_required_preceding_stage(page_name)
    earliest = get_earliest_incomplete_page(current_stage)

    st.warning(
        f"🔒 **{page_name} is currently locked.** Please complete **{preceding}** first.",
        icon="🔒",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f"👉 Current Workflow Position: **{current_stage.value.replace('_', ' ').title()}**")
    with col2:
        if earliest in PAGE_SCRIPT_PATHS:
            if st.button(f"Go to {earliest} ➡️", type="primary", use_container_width=True):
                st.switch_page(PAGE_SCRIPT_PATHS[earliest])

    return False
