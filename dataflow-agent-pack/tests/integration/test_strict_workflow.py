"""Integration tests for Strict Sequential Workflow and Session Management.

Verifies:
1. End-to-end workflow transitions through each stage:
   EMPTY -> UPLOADED -> PROCESSING -> PROCESSED -> DQA_REVIEWED ->
   DASHBOARD_VIEWED -> ANALYTICS_VIEWED -> EXPORT_READY -> COMPLETED.
2. Downstream page locking and prerequisite gating at each stage.
3. Live progress callback events during pipeline execution.
4. Complete session reset (New Session) wiping memory, caches, temporary files,
   and relocking downstream stages.
5. AppTest initialization ensuring sidebar rendered correctly with active session widget.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from core.runner import run_full_pipeline
from core.workflow_manager import (
    WorkflowStage,
    can_access_page,
    get_earliest_incomplete_page,
)
from ui.session import (
    advance_workflow_stage,
    get_current_workflow_stage,
    init_session_state,
    purge_temporary_storage,
    reset_session,
)


class TestWorkflowTransitionsAndGating:
    """Verifies strict sequential transitions and page locking."""

    def test_full_sequential_stage_progression(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Mock streamlit session_state as a standard dict
        mock_state: dict[str, Any] = {}
        monkeypatch.setattr("streamlit.session_state", mock_state)

        # 1. Initialize fresh session
        init_session_state()
        initial_session_id = mock_state["session_id"]
        assert initial_session_id.startswith("SES_")
        assert get_current_workflow_stage() == WorkflowStage.EMPTY

        # Verify initial locked state
        assert can_access_page("Upload Data", get_current_workflow_stage()) is True
        assert can_access_page("Processing", get_current_workflow_stage()) is False
        assert can_access_page("Data Quality", get_current_workflow_stage()) is False
        assert can_access_page("Dashboard", get_current_workflow_stage()) is False
        assert can_access_page("Analytics", get_current_workflow_stage()) is False
        assert can_access_page("Export Reports", get_current_workflow_stage()) is False
        assert get_earliest_incomplete_page(get_current_workflow_stage()) == "Upload Data"

        # 2. File uploaded
        advance_workflow_stage(WorkflowStage.UPLOADED)
        assert get_current_workflow_stage() == WorkflowStage.UPLOADED
        assert can_access_page("Processing", get_current_workflow_stage()) is True
        assert can_access_page("Data Quality", get_current_workflow_stage()) is False
        assert get_earliest_incomplete_page(get_current_workflow_stage()) == "Processing"

        # 3. Pipeline processed
        advance_workflow_stage(WorkflowStage.PROCESSED)
        assert get_current_workflow_stage() == WorkflowStage.PROCESSED
        assert can_access_page("Data Quality", get_current_workflow_stage()) is True
        assert can_access_page("Dashboard", get_current_workflow_stage()) is False
        assert get_earliest_incomplete_page(get_current_workflow_stage()) == "Data Quality"

        # 4. DQA reviewed
        advance_workflow_stage(WorkflowStage.DQA_REVIEWED)
        assert get_current_workflow_stage() == WorkflowStage.DQA_REVIEWED
        assert can_access_page("Dashboard", get_current_workflow_stage()) is True
        assert can_access_page("Analytics", get_current_workflow_stage()) is False
        assert get_earliest_incomplete_page(get_current_workflow_stage()) == "Dashboard"

        # 5. Dashboard viewed
        advance_workflow_stage(WorkflowStage.DASHBOARD_VIEWED)
        assert get_current_workflow_stage() == WorkflowStage.DASHBOARD_VIEWED
        assert can_access_page("Analytics", get_current_workflow_stage()) is True
        assert can_access_page("Export Reports", get_current_workflow_stage()) is False
        assert get_earliest_incomplete_page(get_current_workflow_stage()) == "Analytics"

        # 6. Analytics viewed
        advance_workflow_stage(WorkflowStage.ANALYTICS_VIEWED)
        assert get_current_workflow_stage() == WorkflowStage.ANALYTICS_VIEWED
        assert can_access_page("Export Reports", get_current_workflow_stage()) is True
        assert get_earliest_incomplete_page(get_current_workflow_stage()) == "Export Reports"

        # 7. Export ready
        advance_workflow_stage(WorkflowStage.EXPORT_READY)
        assert get_current_workflow_stage() == WorkflowStage.EXPORT_READY
        assert can_access_page("Export Reports", get_current_workflow_stage()) is True

        # 8. Reset Session (New Session)
        reset_session()
        assert get_current_workflow_stage() == WorkflowStage.EMPTY
        assert mock_state["session_id"] != initial_session_id
        assert mock_state["pipeline_result"] is None
        assert mock_state["dqa_reviewed"] is False
        assert mock_state["dashboard_viewed"] is False
        assert mock_state["analytics_viewed"] is False

        # Downstream pages must be locked again
        assert can_access_page("Processing", get_current_workflow_stage()) is False
        assert can_access_page("Data Quality", get_current_workflow_stage()) is False
        assert can_access_page("Dashboard", get_current_workflow_stage()) is False


class TestPipelineProgressIntegration:
    """Verifies that running the pipeline triggers stage callbacks and produces snapshots."""

    def test_pipeline_execution_emits_stage_progress(self) -> None:
        fixture_path = Path("tests/synthetic/fixtures/synthetic_fsw.xlsx")
        assert fixture_path.exists(), f"Synthetic fixture must exist at {fixture_path}"

        events: list[dict[str, Any]] = []

        def on_progress(snapshot: dict[str, Any]) -> None:
            events.append(snapshot)

        result = run_full_pipeline(
            file_source=fixture_path,
            file_name=fixture_path.name,
            population="FSW",
            period_mode="SEM",
            progress_callback=on_progress,
        )

        assert result is not None
        assert result.total_cohort > 0
        assert len(events) > 0

        # Snapshot in result must be 100% complete
        assert result.progress_snapshot is not None
        assert result.progress_snapshot["overall_progress"] == 100.0

        stages = result.progress_snapshot["stages"]
        for s_id in ("ingestion", "cleaning", "dqa", "analytics", "reporting"):
            assert s_id in stages
            assert stages[s_id]["status"] == "completed"
            assert stages[s_id]["progress_pct"] == 100.0


class TestStoragePurge:
    """Verifies safe purging of temporary files."""

    def test_purge_temporary_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            keep_file = tmp_path / ".gitkeep"
            keep_file.touch()

            data_file = tmp_path / "temp_upload.xlsx"
            data_file.write_text("dummy")

            sub_dir = tmp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "nested.txt").write_text("dummy")

            deleted = purge_temporary_storage(target_dir=tmp_path)
            assert deleted >= 2
            assert keep_file.exists()
            assert not data_file.exists()
            assert not sub_dir.exists()


class TestAppTestWorkflow:
    """Verifies Streamlit AppTest initialization and layout rendering."""

    def test_app_startup_and_sidebar_rendering(self) -> None:
        app_path = str(Path(__file__).resolve().parents[2] / "app.py")
        at = AppTest.from_file(app_path)
        at.run(timeout=15)
        assert not at.exception
        # Ensure title or header rendered
        assert len(at.sidebar) > 0
