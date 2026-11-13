"""Unit tests for Central Progress Manager (core/progress_manager.py).

Verifies:
- Configurable stage weights summing to 100%.
- Normalized overall progress computation (capped at 99% until all stages complete).
- Stage state lifecycle (pending -> running -> completed / failed).
- Sub-operation tracking, metrics storage, and event notifications.
- Resilience against callback exceptions.
- Serializable JSON snapshot format.
"""

from __future__ import annotations

import json
from typing import Any

from core.progress_manager import (
    DEFAULT_STAGE_WEIGHTS,
    STAGE_NAMES,
    ProgressManager,
)


class TestProgressManagerWeights:
    """Verifies stage weighting logic."""

    def test_default_weights_sum_to_100(self) -> None:
        assert sum(DEFAULT_STAGE_WEIGHTS.values()) == 100.0
        assert set(DEFAULT_STAGE_WEIGHTS.keys()) == {
            "ingestion",
            "cleaning",
            "dqa",
            "analytics",
            "reporting",
        }

    def test_stage_names_and_numbering(self) -> None:
        assert len(STAGE_NAMES) == 5
        for idx, (s_id, (s_num, _s_name)) in enumerate(STAGE_NAMES.items(), start=1):
            assert s_num == idx
            assert s_id in DEFAULT_STAGE_WEIGHTS


class TestProgressManagerCalculations:
    """Verifies weighted progress arithmetic and caps."""

    def test_initial_progress_is_zero(self) -> None:
        pm = ProgressManager()
        assert pm.overall_progress == 0.0
        for stage in pm.stages.values():
            assert stage.status == "pending"
            assert stage.progress_pct == 0.0

    def test_single_stage_completion(self) -> None:
        pm = ProgressManager()
        pm.complete_stage("ingestion")
        # Ingestion weight is 10.0%
        assert pm.stages["ingestion"].status == "completed"
        assert pm.stages["ingestion"].progress_pct == 100.0
        assert pm.overall_progress == 10.0

    def test_cumulative_stage_completion(self) -> None:
        pm = ProgressManager()
        pm.complete_stage("ingestion")  # 10
        pm.complete_stage("cleaning")   # 15
        assert pm.overall_progress == 25.0

        pm.complete_stage("dqa")        # 20
        assert pm.overall_progress == 45.0

        pm.complete_stage("analytics")  # 35
        assert pm.overall_progress == 80.0

    def test_near_completion_capped_at_99_until_all_completed(self) -> None:
        pm = ProgressManager()
        pm.complete_stage("ingestion")  # 10
        pm.complete_stage("cleaning")   # 15
        pm.complete_stage("dqa")        # 20
        pm.complete_stage("analytics")  # 35
        # Total so far: 80. Now reporting is running at 99% progress (99% of 20 = 19.8) -> 99.8%
        pm.start_stage("reporting")
        pm.update_progress("reporting", 99.0)
        assert pm.overall_progress == 99.0  # Capped at 99.0%

        # Explicit completion unlocks 100.0%
        pm.complete_stage("reporting")
        assert pm.overall_progress == 100.0


class TestStageLifecycleAndOperations:
    """Verifies lifecycle events and sub-operation tracking."""

    def test_start_stage(self) -> None:
        pm = ProgressManager()
        pm.start_stage("cleaning", "Vectorizing dates...")
        stage = pm.stages["cleaning"]
        assert stage.status == "running"
        assert stage.current_operation == "Vectorizing dates..."

    def test_update_progress_and_metrics(self) -> None:
        pm = ProgressManager()
        pm.start_stage("dqa")
        pm.update_progress(
            "dqa",
            50.0,
            operation="Checking Rule R10",
            completed_op="Rule R09 passed",
            metrics={"passed_rules": 9, "failed_rules": 0},
        )
        stage = pm.stages["dqa"]
        assert stage.progress_pct == 50.0
        assert stage.current_operation == "Checking Rule R10"
        assert "Rule R09 passed" in stage.completed_operations
        assert stage.metrics["passed_rules"] == 9

    def test_fail_stage(self) -> None:
        pm = ProgressManager()
        pm.start_stage("analytics")
        pm.fail_stage("analytics", "Missing required column: Sex")
        stage = pm.stages["analytics"]
        assert stage.status == "failed"
        assert stage.error_message == "Missing required column: Sex"
        assert "Failed:" in stage.current_operation


class TestEventNotificationsAndSnapshot:
    """Verifies event dispatching and snapshot format."""

    def test_callback_invoked_on_update(self) -> None:
        events: list[dict[str, Any]] = []

        def on_progress(snapshot: dict[str, Any]) -> None:
            events.append(snapshot)

        pm = ProgressManager(callback=on_progress)
        pm.start_stage("ingestion", "Opening file")
        pm.update_progress("ingestion", 50.0, "Parsing rows")
        pm.complete_stage("ingestion")

        assert len(events) == 3
        assert events[0]["stages"]["ingestion"]["status"] == "running"
        assert events[1]["stages"]["ingestion"]["progress_pct"] == 50.0
        assert events[2]["stages"]["ingestion"]["status"] == "completed"

    def test_resilience_to_callback_failure(self) -> None:
        def faulty_callback(_: dict[str, Any]) -> None:
            raise RuntimeError("UI render failure simulated")

        pm = ProgressManager(callback=faulty_callback)
        # Should not raise exception
        pm.start_stage("ingestion")
        pm.update_progress("ingestion", 20.0)
        pm.complete_stage("ingestion")
        assert pm.stages["ingestion"].status == "completed"

    def test_duration_tracking_in_minutes_and_seconds(self) -> None:
        pm = ProgressManager()
        pm.start_stage("analytics")
        pm.complete_stage("analytics", metrics={"duration_seconds": 120.0})
        stage = pm.stages["analytics"]
        assert stage.duration_seconds == 120.0
        assert stage.duration_minutes == 2.0

        snap = pm.snapshot()
        assert snap["stages"]["analytics"]["duration_seconds"] == 120.0
        assert snap["stages"]["analytics"]["duration_minutes"] == 2.0


    def test_snapshot_json_serializable(self) -> None:
        pm = ProgressManager()
        pm.start_stage("ingestion")
        pm.update_progress("ingestion", 60.0, "Reading sheet", metrics={"rows": 5000})
        snap = pm.snapshot()

        serialized = json.dumps(snap)
        assert isinstance(serialized, str)
        deserialized = json.loads(serialized)
        assert deserialized["overall_progress"] == 6.0  # 60% of 10% weight = 6%
        assert deserialized["stages"]["ingestion"]["metrics"]["rows"] == 5000
