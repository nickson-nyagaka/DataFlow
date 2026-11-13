"""Unit tests for Central Workflow State Machine (core/workflow_manager.py).

Verifies:
- WorkflowStage enumeration and robust stage normalization.
- Strict sequential access permissions per page.
- Earliest incomplete page resolution.
- Required preceding stage messages for informative user feedback.
- PAGE_SCRIPT_PATHS mapping and physical file existence.
- Workflow checklist generation for sidebar visualization.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.workflow_manager import (
    PAGE_SCRIPT_PATHS,
    WorkflowStage,
    can_access_page,
    get_earliest_incomplete_page,
    get_required_preceding_stage,
    get_workflow_checklist,
    normalize_stage,
)


class TestWorkflowStageNormalization:
    """Verifies safe coercion and backwards compatibility of workflow stage strings."""

    def test_normalize_valid_stages(self) -> None:
        assert normalize_stage(WorkflowStage.EMPTY) == WorkflowStage.EMPTY
        assert normalize_stage("empty") == WorkflowStage.EMPTY
        assert normalize_stage("EMPTY") == WorkflowStage.EMPTY
        assert normalize_stage("uploaded") == WorkflowStage.UPLOADED
        assert normalize_stage("processing") == WorkflowStage.PROCESSING
        assert normalize_stage("processed") == WorkflowStage.PROCESSED
        assert normalize_stage("dqa_reviewed") == WorkflowStage.DQA_REVIEWED
        assert normalize_stage("dashboard_viewed") == WorkflowStage.DASHBOARD_VIEWED
        assert normalize_stage("analytics_viewed") == WorkflowStage.ANALYTICS_VIEWED
        assert normalize_stage("export_ready") == WorkflowStage.EXPORT_READY
        assert normalize_stage("completed") == WorkflowStage.COMPLETED

    def test_normalize_legacy_and_edge_cases(self) -> None:
        assert normalize_stage("idle") == WorkflowStage.EMPTY
        assert normalize_stage("  UPLOADED  ") == WorkflowStage.UPLOADED
        assert normalize_stage(None) == WorkflowStage.EMPTY
        assert normalize_stage("unknown_invalid_stage") == WorkflowStage.EMPTY


class TestPageAccessGating:
    """Verifies strict sequential gating preventing stage-skipping."""

    def test_system_pages_always_accessible(self) -> None:
        for stage in WorkflowStage:
            assert can_access_page("Configuration", stage) is True
            assert can_access_page("About", stage) is True

    def test_upload_data_always_accessible(self) -> None:
        for stage in WorkflowStage:
            assert can_access_page("Upload Data", stage) is True

    def test_stage_empty_locks_downstream(self) -> None:
        assert can_access_page("Processing", WorkflowStage.EMPTY) is False
        assert can_access_page("Data Quality", WorkflowStage.EMPTY) is False
        assert can_access_page("Dashboard", WorkflowStage.EMPTY) is False
        assert can_access_page("Analytics", WorkflowStage.EMPTY) is False
        assert can_access_page("Export Reports", WorkflowStage.EMPTY) is False

    def test_stage_uploaded_unlocks_processing(self) -> None:
        assert can_access_page("Processing", WorkflowStage.UPLOADED) is True
        assert can_access_page("Data Quality", WorkflowStage.UPLOADED) is False
        assert can_access_page("Dashboard", WorkflowStage.UPLOADED) is False
        assert can_access_page("Analytics", WorkflowStage.UPLOADED) is False
        assert can_access_page("Export Reports", WorkflowStage.UPLOADED) is False

    def test_stage_processed_unlocks_data_quality(self) -> None:
        assert can_access_page("Processing", WorkflowStage.PROCESSED) is True
        assert can_access_page("Data Quality", WorkflowStage.PROCESSED) is True
        assert can_access_page("Dashboard", WorkflowStage.PROCESSED) is False
        assert can_access_page("Analytics", WorkflowStage.PROCESSED) is False
        assert can_access_page("Export Reports", WorkflowStage.PROCESSED) is False

    def test_stage_dqa_reviewed_unlocks_dashboard(self) -> None:
        assert can_access_page("Data Quality", WorkflowStage.DQA_REVIEWED) is True
        assert can_access_page("Dashboard", WorkflowStage.DQA_REVIEWED) is True
        assert can_access_page("Analytics", WorkflowStage.DQA_REVIEWED) is False
        assert can_access_page("Export Reports", WorkflowStage.DQA_REVIEWED) is False

    def test_stage_dashboard_viewed_unlocks_analytics(self) -> None:
        assert can_access_page("Dashboard", WorkflowStage.DASHBOARD_VIEWED) is True
        assert can_access_page("Analytics", WorkflowStage.DASHBOARD_VIEWED) is True
        assert can_access_page("Export Reports", WorkflowStage.DASHBOARD_VIEWED) is False

    def test_stage_analytics_viewed_unlocks_export_reports(self) -> None:
        assert can_access_page("Analytics", WorkflowStage.ANALYTICS_VIEWED) is True
        assert can_access_page("Export Reports", WorkflowStage.ANALYTICS_VIEWED) is True

    def test_stage_export_ready_and_completed_unlock_all(self) -> None:
        for stage in (WorkflowStage.EXPORT_READY, WorkflowStage.COMPLETED):
            for page in (
                "Upload Data",
                "Processing",
                "Data Quality",
                "Dashboard",
                "Analytics",
                "Export Reports",
            ):
                assert can_access_page(page, stage) is True


class TestEarliestIncompletePage:
    """Verifies calculation of next action for guidance buttons."""

    @pytest.mark.parametrize(
        ("current_stage", "expected_page"),
        [
            (WorkflowStage.EMPTY, "Upload Data"),
            (WorkflowStage.UPLOADED, "Processing"),
            (WorkflowStage.PROCESSING, "Processing"),
            (WorkflowStage.PROCESSED, "Data Quality"),
            (WorkflowStage.DQA_REVIEWED, "Dashboard"),
            (WorkflowStage.DASHBOARD_VIEWED, "Analytics"),
            (WorkflowStage.ANALYTICS_VIEWED, "Export Reports"),
            (WorkflowStage.EXPORT_READY, "Export Reports"),
            (WorkflowStage.COMPLETED, "Export Reports"),
        ],
    )
    def test_get_earliest_incomplete_page(
        self, current_stage: WorkflowStage, expected_page: str
    ) -> None:
        assert get_earliest_incomplete_page(current_stage) == expected_page


class TestPrecedingStageInfo:
    """Verifies informative messages for denied navigation."""

    def test_preceding_stage_names(self) -> None:
        assert get_required_preceding_stage("Processing") == "Upload Data"
        assert get_required_preceding_stage("Data Quality") == "Processing"
        assert get_required_preceding_stage("Dashboard") == "Data Quality review"
        assert get_required_preceding_stage("Analytics") == "Dashboard"
        assert get_required_preceding_stage("Export Reports") == "Analytics"


class TestPageScriptPaths:
    """Verifies script mapping validity and file existence."""

    def test_all_pages_mapped_and_files_exist(self) -> None:
        expected_pages = [
            "Upload Data",
            "Processing",
            "Data Quality",
            "Dashboard",
            "Analytics",
            "Export Reports",
            "Configuration",
            "About",
        ]
        for page in expected_pages:
            assert page in PAGE_SCRIPT_PATHS
            path_str = PAGE_SCRIPT_PATHS[page]
            p = Path(path_str)
            assert p.exists(), f"Script file for {page} must exist at {path_str}"


class TestWorkflowChecklist:
    """Verifies checklist status generation for the active session widget."""

    def test_initial_state_checklist(self) -> None:
        checklist = get_workflow_checklist(WorkflowStage.EMPTY)
        assert len(checklist) == 6
        assert checklist[0]["title"] == "Upload Data"
        assert checklist[0]["icon"] == "●"
        assert checklist[0]["is_current"] is True
        assert checklist[0]["is_completed"] is False

        # All subsequent items should be locked
        for item in checklist[1:]:
            assert item["icon"] == "○"
            assert item["is_completed"] is False
            assert item["is_unlocked"] is False

    def test_dqa_reviewed_checklist(self) -> None:
        checklist = get_workflow_checklist(WorkflowStage.DQA_REVIEWED)
        # Upload Data, Processing, Data Quality should be completed
        assert checklist[0]["is_completed"] is True
        assert checklist[0]["icon"] == "✓"
        assert checklist[1]["is_completed"] is True
        assert checklist[1]["icon"] == "✓"
        assert checklist[2]["is_completed"] is True
        assert checklist[2]["icon"] == "✓"

        # Dashboard should be current
        assert checklist[3]["title"] == "Dashboard"
        assert checklist[3]["is_current"] is True
        assert checklist[3]["icon"] == "●"

        # Analytics and Exports should be pending/locked
        assert checklist[4]["is_completed"] is False
        assert checklist[5]["is_completed"] is False
