"""Critical DQA Override Manager and Audit Logger.

Implements Decision D-042:
- Export gating: blocks summary, indicator, and ZIP exports when unoverridden Critical DQA exceptions exist.
- Multi-field override: requires authorized person name and >= 20 char reason per rule.
- Hash-and-count binding: overrides are tied strictly to input file hash and rule count; data change invalidates.
- Output stamping: marks overridden packages as PROVISIONAL.
- Advisory mode: allows export with warning and PROVISIONAL stamp when block_on_critical is False.
- Fail closed: if DQA fails or cannot run, export is blocked and overrides cannot bypass.
- Append-only audit logging in runtime/audit/override_log.jsonl (zero personal identifiers).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.validation import DQAResults


@dataclass(frozen=True)
class RuleOverride:
    """An authorized override for a single Critical DQA rule."""

    rule_id: str
    authorized_by: str
    reason: str
    file_hash: str
    exception_count: int
    timestamp: str  # ISO-8601 UTC

    def is_valid_for(self, file_hash: str, current_count: int) -> bool:
        """Override is valid only if input hash and exception count match exactly."""
        return (self.file_hash == file_hash) and (self.exception_count == current_count)


class OverrideManager:
    """Manages session overrides, gating logic, and audit trail."""

    def __init__(self, audit_log_path: Path | str = "runtime/audit/override_log.jsonl") -> None:
        self.audit_log_path = Path(audit_log_path)
        self._overrides: dict[str, RuleOverride] = {}

    def clear(self) -> None:
        """Clears all session overrides."""
        self._overrides.clear()

    @property
    def overrides(self) -> dict[str, RuleOverride]:
        """Returns shallow copy of active session overrides."""
        return dict(self._overrides)

    def record_override(
        self,
        rule_id: str,
        authorized_by: str,
        reason: str,
        file_hash: str,
        exception_count: int,
    ) -> RuleOverride:
        """
        Validates, registers, and audits an authorized override.

        Raises ValueError if inputs are invalid.
        """
        auth_clean = authorized_by.strip()
        if not auth_clean:
            raise ValueError("Authorized user name is required for Critical DQA override.")

        reason_clean = reason.strip()
        if len(reason_clean) < 20:
            raise ValueError(
                f"Override justification must be at least 20 characters (provided {len(reason_clean)})."
            )

        if exception_count <= 0:
            raise ValueError(
                f"Cannot override rule {rule_id} with non-positive count ({exception_count})."
            )

        if not file_hash or file_hash == "N/A":
            raise ValueError("Valid file hash is required to anchor Critical DQA override.")

        ts = datetime.now(UTC).isoformat()
        override = RuleOverride(
            rule_id=rule_id,
            authorized_by=auth_clean,
            reason=reason_clean,
            file_hash=file_hash,
            exception_count=exception_count,
            timestamp=ts,
        )

        self._overrides[rule_id] = override
        self._append_audit_log(override)
        return override

    def _append_audit_log(self, override: RuleOverride) -> None:
        """Appends override record to runtime audit log with zero patient identifiers."""
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "event": "CRITICAL_DQA_OVERRIDE",
            "rule_id": override.rule_id,
            "exception_count": override.exception_count,
            "authorized_by": override.authorized_by,
            "reason": override.reason,
            "file_hash": override.file_hash,
            "timestamp": override.timestamp,
        }
        with open(self.audit_log_path, mode="a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def check_export_status(
        self,
        dqa_results: DQAResults | None,
        file_hash: str,
        block_on_critical: bool = True,
    ) -> tuple[bool, list[str], bool]:
        """
        Evaluates whether report exports are permitted.

        Returns:
            (is_blocked, blocking_reasons, is_provisional)
        """
        # Fail closed: if DQA results are absent or execution failed
        if dqa_results is None:
            return (
                True,
                ["DQA validation has not been run or failed to complete (Fail Closed policy)."],
                False,
            )

        critical_counts = dqa_results.get_critical_counts()
        if not critical_counts:
            # Clean run: not blocked, not provisional
            return (False, [], False)

        # Advisory mode (block_on_critical = False)
        if not block_on_critical:
            # Allowed, but marked PROVISIONAL
            return (False, [], True)

        # Enforced mode: check each critical rule against registered overrides
        blocking_rules: list[str] = []

        for rule_id, count in critical_counts.items():
            override = self._overrides.get(rule_id)
            if not (override and override.is_valid_for(file_hash=file_hash, current_count=count)):
                blocking_rules.append(f"{rule_id} ({count} exceptions)")

        if blocking_rules:
            reasons = [
                f"Export blocked by Critical DQA exception(s): {', '.join(blocking_rules)}. "
                "Correct source file or authorize an override with justification."
            ]
            return (True, reasons, False)

        # All critical exceptions were validly overridden
        return (False, [], True)

    def get_provisional_reasons(
        self,
        dqa_results: DQAResults | None,
        file_hash: str,
        block_on_critical: bool = True,
    ) -> list[str]:
        """Returns list of rule IDs or causes leading to PROVISIONAL stamping."""
        if dqa_results is None:
            return []

        critical_counts = dqa_results.get_critical_counts()
        if not critical_counts:
            return []

        if not block_on_critical:
            return [f"ADVISORY_MODE:{rule}({cnt})" for rule, cnt in critical_counts.items()]

        provisional = []
        for rule_id, count in critical_counts.items():
            override = self._overrides.get(rule_id)
            if override and override.is_valid_for(file_hash=file_hash, current_count=count):
                provisional.append(f"OVERRIDDEN:{rule_id}({count})")
        return provisional
