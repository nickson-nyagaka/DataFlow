"""Central Workflow State Machine and Navigation Guard for DATAFLOW.

Governs strict sequential workflow progression, page-level access permissions,
and stage transitions per Master Brief §3, §4, and §5.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class WorkflowStage(StrEnum):
    EMPTY = "empty"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    DQA_REVIEWED = "dqa_reviewed"
    DASHBOARD_VIEWED = "dashboard_viewed"
    ANALYTICS_VIEWED = "analytics_viewed"
    EXPORT_READY = "export_ready"
    COMPLETED = "completed"


# Progression rank for evaluating unlocked state
_STAGE_RANK: dict[WorkflowStage, int] = {
    WorkflowStage.EMPTY: 0,
    WorkflowStage.UPLOADED: 1,
    WorkflowStage.PROCESSING: 2,
    WorkflowStage.PROCESSED: 3,
    WorkflowStage.DQA_REVIEWED: 4,
    WorkflowStage.DASHBOARD_VIEWED: 5,
    WorkflowStage.ANALYTICS_VIEWED: 6,
    WorkflowStage.EXPORT_READY: 7,
    WorkflowStage.COMPLETED: 8,
}

# The minimum stage required to unlock each workflow page
_PAGE_REQUIRED_STAGE: dict[str, WorkflowStage] = {
    "Upload Data": WorkflowStage.EMPTY,
    "Processing": WorkflowStage.UPLOADED,
    "Data Quality": WorkflowStage.PROCESSED,
    "Dashboard": WorkflowStage.DQA_REVIEWED,
    "Analytics": WorkflowStage.DASHBOARD_VIEWED,
    "Export Reports": WorkflowStage.ANALYTICS_VIEWED,
}

# Preceding stage names for informative rejection messages
_PAGE_PRECEDING_STAGE_NAME: dict[str, str] = {
    "Processing": "Upload Data",
    "Data Quality": "Processing",
    "Dashboard": "Data Quality review",
    "Analytics": "Dashboard",
    "Export Reports": "Analytics",
}

# Page script path mapping for Streamlit st.switch_page
PAGE_SCRIPT_PATHS: dict[str, str] = {
    "Upload Data": "ui/upload.py",
    "Processing": "ui/processing.py",
    "Data Quality": "ui/data_quality.py",
    "Dashboard": "ui/dashboard.py",
    "Analytics": "ui/analytics.py",
    "Export Reports": "ui/exports.py",
    "Configuration": "ui/configuration.py",
    "About": "ui/about.py",
}


def normalize_stage(stage: str | WorkflowStage | None) -> WorkflowStage:
    """Safely coerces strings or existing enums to WorkflowStage."""
    if stage is None:
        return WorkflowStage.EMPTY
    if isinstance(stage, WorkflowStage):
        return stage
    s = str(stage).strip().lower()
    for member in WorkflowStage:
        if member.value == s or member.name.lower() == s:
            return member
    # Map legacy stage strings
    if s == "idle":
        return WorkflowStage.EMPTY
    return WorkflowStage.EMPTY


def can_access_page(page_name: str, current_stage: str | WorkflowStage) -> bool:
    """Determines whether a page can be accessed given the current workflow stage.

    System pages ('Configuration', 'About') are always accessible.
    Upload Data is always accessible.
    Downstream pages require their strict prerequisites to be satisfied.
    """
    clean_name = page_name.strip()
    if clean_name in ("Configuration", "About", "Upload Data"):
        return True

    stage_enum = normalize_stage(current_stage)
    required_stage = _PAGE_REQUIRED_STAGE.get(clean_name)
    if required_stage is None:
        return True

    return _STAGE_RANK[stage_enum] >= _STAGE_RANK[required_stage]


def get_required_preceding_stage(page_name: str) -> str:
    """Returns human-readable name of prerequisite stage for access denials."""
    clean_name = page_name.strip()
    return _PAGE_PRECEDING_STAGE_NAME.get(clean_name, "the required preceding stage")


def get_earliest_incomplete_page(current_stage: str | WorkflowStage) -> str:
    """Returns the title of the next required workflow page to complete."""
    stage_enum = normalize_stage(current_stage)
    if stage_enum == WorkflowStage.EMPTY:
        return "Upload Data"
    if stage_enum in (WorkflowStage.UPLOADED, WorkflowStage.PROCESSING):
        return "Processing"
    if stage_enum == WorkflowStage.PROCESSED:
        return "Data Quality"
    if stage_enum == WorkflowStage.DQA_REVIEWED:
        return "Dashboard"
    if stage_enum == WorkflowStage.DASHBOARD_VIEWED:
        return "Analytics"
    if stage_enum in (WorkflowStage.ANALYTICS_VIEWED, WorkflowStage.EXPORT_READY):
        return "Export Reports"
    return "Export Reports"


def get_workflow_checklist(current_stage: str | WorkflowStage) -> list[dict[str, Any]]:
    """Generates visual checklist state for Active Session sidebar display.

    Returns a list of dicts with:
      - name: str
      - status_icon: '✓' (completed), '●' (current), '○' (locked/pending)
      - is_current: bool
      - is_unlocked: bool
    """
    stage_enum = normalize_stage(current_stage)
    current_rank = _STAGE_RANK[stage_enum]

    steps = [
        ("Upload Data", WorkflowStage.EMPTY, 1),
        ("Processing", WorkflowStage.UPLOADED, 3),
        ("Data Quality", WorkflowStage.PROCESSED, 4),
        ("Dashboard", WorkflowStage.DQA_REVIEWED, 5),
        ("Analytics", WorkflowStage.DASHBOARD_VIEWED, 6),
        ("Export Reports", WorkflowStage.ANALYTICS_VIEWED, 8),
    ]

    checklist = []
    for title, unlock_stage, complete_rank in steps:
        is_unlocked = current_rank >= _STAGE_RANK[unlock_stage]
        is_completed = current_rank >= complete_rank
        # Mark as active if it's the current target
        is_current = (not is_completed) and is_unlocked

        if is_completed:
            icon = "✓"
        elif is_current:
            icon = "●"
        else:
            icon = "○"

        checklist.append(
            {
                "title": title,
                "icon": icon,
                "is_completed": is_completed,
                "is_current": is_current,
                "is_unlocked": is_unlocked,
            }
        )
    return checklist
