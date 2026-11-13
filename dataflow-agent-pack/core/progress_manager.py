"""Central Progress Manager and Event Dispatcher for DATAFLOW.

Implements Master Brief §8, §9, and §10:
- Independent tracking for all 5 analytical stages.
- Configurable stage weights with mathematically normalized overall progress calculation.
- Granular sub-operation tracking and event emission.
- Decoupled from Streamlit UI rendering.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageProgress:
    stage_id: str
    stage_number: int
    name: str
    weight: float
    status: str = "pending"  # "pending", "running", "completed", "failed"
    progress_pct: float = 0.0
    current_operation: str = "Pending execution"
    completed_operations: list[str] = field(default_factory=list)
    pending_operations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    start_time: float | None = None
    duration_seconds: float = 0.0
    duration_minutes: float = 0.0


DEFAULT_STAGE_WEIGHTS: dict[str, float] = {
    "ingestion": 10.0,
    "cleaning": 15.0,
    "dqa": 20.0,
    "analytics": 35.0,
    "reporting": 20.0,
}

STAGE_NAMES: dict[str, tuple[int, str]] = {
    "ingestion": (1, "📥 Stage 1: Workbook Ingestion"),
    "cleaning": (2, "🧹 Stage 2: Data Cleaning & Normalization"),
    "dqa": (3, "🛡️ Stage 3: Data Quality Assessment (DQA)"),
    "analytics": (4, "📈 Stage 4: Analytical Calculations"),
    "reporting": (5, "📦 Stage 5: Reporting Package Assembly"),
}


class ProgressManager:
    """Manages granular stage progress and overall pipeline completion."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.weights = weights or dict(DEFAULT_STAGE_WEIGHTS)
        self.callback = callback
        self.total_weight = sum(self.weights.values()) or 100.0

        self.stages: dict[str, StageProgress] = {}
        for s_id, (s_num, s_name) in STAGE_NAMES.items():
            self.stages[s_id] = StageProgress(
                stage_id=s_id,
                stage_number=s_num,
                name=s_name,
                weight=self.weights.get(s_id, 20.0),
            )

    @property
    def overall_progress(self) -> float:
        """Calculates normalized overall progress percentage (0.0 to 100.0).

        A stage must not contribute more than its weight. Overall progress
        can only reach 100.0% when all five stages are marked 'completed'.
        """
        all_completed = all(s.status == "completed" for s in self.stages.values())
        if all_completed:
            return 100.0

        weighted_sum = sum(
            (s.progress_pct / 100.0) * s.weight for s in self.stages.values()
        )
        calculated = (weighted_sum / self.total_weight) * 100.0
        # Cap at 99.0% until all stages are explicitly completed
        return min(round(calculated, 1), 99.0)

    def start_stage(self, stage_id: str, operation: str = "Starting stage...") -> None:
        """Marks a stage as running."""
        stage = self.stages.get(stage_id)
        if stage:
            stage.status = "running"
            stage.start_time = time.perf_counter()
            stage.current_operation = operation
            self._notify(stage_id)

    def update_progress(
        self,
        stage_id: str,
        progress_pct: float,
        operation: str | None = None,
        completed_op: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Updates progress within an active stage."""
        stage = self.stages.get(stage_id)
        if not stage:
            return

        stage.progress_pct = max(0.0, min(100.0, float(progress_pct)))
        if stage.start_time is not None:
            stage.duration_seconds = round(time.perf_counter() - stage.start_time, 2)
            stage.duration_minutes = round(stage.duration_seconds / 60.0, 3)
        if operation:
            stage.current_operation = operation
        if completed_op and completed_op not in stage.completed_operations:
            stage.completed_operations.append(completed_op)
        if metrics:
            stage.metrics.update(metrics)
            if "duration_seconds" in metrics:
                stage.duration_seconds = float(metrics["duration_seconds"])
                stage.duration_minutes = round(stage.duration_seconds / 60.0, 3)

        self._notify(stage_id)

    def complete_stage(
        self,
        stage_id: str,
        final_op: str = "Stage completed successfully",
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Marks a stage as 100% completed."""
        stage = self.stages.get(stage_id)
        if not stage:
            return

        stage.status = "completed"
        stage.progress_pct = 100.0
        if stage.start_time is not None:
            stage.duration_seconds = round(time.perf_counter() - stage.start_time, 2)
            stage.duration_minutes = round(stage.duration_seconds / 60.0, 3)
        stage.current_operation = final_op
        if metrics:
            stage.metrics.update(metrics)
            if "duration_seconds" in metrics:
                stage.duration_seconds = float(metrics["duration_seconds"])
                stage.duration_minutes = round(stage.duration_seconds / 60.0, 3)

        self._notify(stage_id)

    def fail_stage(self, stage_id: str, error_message: str) -> None:
        """Marks a stage as failed."""
        stage = self.stages.get(stage_id)
        if not stage:
            return

        stage.status = "failed"
        if stage.start_time is not None:
            stage.duration_seconds = round(time.perf_counter() - stage.start_time, 2)
            stage.duration_minutes = round(stage.duration_seconds / 60.0, 3)
        stage.error_message = error_message
        stage.current_operation = f"Failed: {error_message}"
        self._notify(stage_id)

    def snapshot(self) -> dict[str, Any]:
        """Returns a serializable dictionary snapshot of current progress."""
        return {
            "overall_progress": self.overall_progress,
            "stages": {
                s_id: {
                    "stage_id": s.stage_id,
                    "stage_number": s.stage_number,
                    "name": s.name,
                    "status": s.status,
                    "progress_pct": s.progress_pct,
                    "current_operation": s.current_operation,
                    "completed_operations": list(s.completed_operations),
                    "metrics": dict(s.metrics),
                    "error_message": s.error_message,
                    "duration_seconds": s.duration_seconds,
                    "duration_minutes": s.duration_minutes,
                }
                for s_id, s in self.stages.items()
            },
        }

    def _notify(self, stage_id: str) -> None:
        if self.callback:
            try:
                self.callback(self.snapshot())
            except Exception:
                pass
