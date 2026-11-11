"""Unit tests for core/override.py (Decision D-042)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from core.override import OverrideManager
from core.validation import DQAResults


@pytest.fixture
def temp_audit_log(tmp_path: Path) -> Path:
    return tmp_path / "runtime" / "audit" / "override_log.jsonl"


@pytest.fixture
def sample_dqa_results() -> DQAResults:
    exceptions_df = pd.DataFrame(
        [
            {"rule_id": "DQA_DUPLICATE_UIC", "severity": "Critical", "uic": "UIC-001"},
            {"rule_id": "DQA_DUPLICATE_UIC", "severity": "Critical", "uic": "UIC-002"},
            {"rule_id": "DQA_HIV_POS_NO_ART", "severity": "Major", "uic": "UIC-003"},
        ]
    )
    summary_df = pd.DataFrame()
    return DQAResults(
        exceptions_df=exceptions_df,
        summary_df=summary_df,
        rule_counts={"DQA_DUPLICATE_UIC": 2, "DQA_HIV_POS_NO_ART": 1},
        severity_counts={"Critical": 2, "Major": 1},
        has_critical=True,
        total_exceptions=3,
    )


def test_override_manager_validation(temp_audit_log: Path):
    manager = OverrideManager(audit_log_path=temp_audit_log)

    # Empty name fails
    with pytest.raises(ValueError, match="Authorized user name is required"):
        manager.record_override(
            rule_id="DQA_DUPLICATE_UIC",
            authorized_by="  ",
            reason="Justification with more than twenty characters here.",
            file_hash="hash123",
            exception_count=2,
        )

    # Short reason fails (<20 chars)
    with pytest.raises(ValueError, match="at least 20 characters"):
        manager.record_override(
            rule_id="DQA_DUPLICATE_UIC",
            authorized_by="Dr. Jane",
            reason="Too short",
            file_hash="hash123",
            exception_count=2,
        )

    # Non-positive count fails
    with pytest.raises(ValueError, match="non-positive count"):
        manager.record_override(
            rule_id="DQA_DUPLICATE_UIC",
            authorized_by="Dr. Jane",
            reason="Justification with more than twenty characters here.",
            file_hash="hash123",
            exception_count=0,
        )

    # Missing file hash fails
    with pytest.raises(ValueError, match="Valid file hash is required"):
        manager.record_override(
            rule_id="DQA_DUPLICATE_UIC",
            authorized_by="Dr. Jane",
            reason="Justification with more than twenty characters here.",
            file_hash="",
            exception_count=2,
        )


def test_override_audit_logging_no_pii(temp_audit_log: Path):
    manager = OverrideManager(audit_log_path=temp_audit_log)
    override = manager.record_override(
        rule_id="DQA_DUPLICATE_UIC",
        authorized_by="Analyst Bob",
        reason="Partner confirmed duplicate encounters will be reconciled at end of month.",
        file_hash="sha256abc123",
        exception_count=5,
    )

    assert override.rule_id == "DQA_DUPLICATE_UIC"
    assert temp_audit_log.exists()

    with open(temp_audit_log, encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "CRITICAL_DQA_OVERRIDE"
    assert record["rule_id"] == "DQA_DUPLICATE_UIC"
    assert record["exception_count"] == 5
    assert record["authorized_by"] == "Analyst Bob"
    # Ensure no patient identifiers or client values are logged
    assert "uic-" not in json.dumps(record).lower()
    assert "patient" not in json.dumps(record).lower()


def test_fail_closed_policy(temp_audit_log: Path):
    manager = OverrideManager(audit_log_path=temp_audit_log)

    # None DQA results blocks export immediately
    is_blocked, reasons, is_prov = manager.check_export_status(
        dqa_results=None,
        file_hash="hash123",
        block_on_critical=True,
    )
    assert is_blocked is True
    assert "Fail Closed" in reasons[0]
    assert is_prov is False


def test_export_gating_and_hash_invalidation(temp_audit_log: Path, sample_dqa_results: DQAResults):
    manager = OverrideManager(audit_log_path=temp_audit_log)

    # 1. Unoverridden critical exception blocks export
    is_blocked, reasons, is_prov = manager.check_export_status(
        dqa_results=sample_dqa_results,
        file_hash="hash123",
        block_on_critical=True,
    )
    assert is_blocked is True
    assert "DQA_DUPLICATE_UIC" in reasons[0]
    assert is_prov is False

    # 2. Record valid override
    manager.record_override(
        rule_id="DQA_DUPLICATE_UIC",
        authorized_by="Supervisor Jane",
        reason="Verified distinct clients with clinic; UIC typo will be updated next quarter.",
        file_hash="hash123",
        exception_count=2,
    )

    is_blocked, reasons, is_prov = manager.check_export_status(
        dqa_results=sample_dqa_results,
        file_hash="hash123",
        block_on_critical=True,
    )
    assert is_blocked is False
    assert is_prov is True
    prov_reasons = manager.get_provisional_reasons(sample_dqa_results, "hash123", True)
    assert "OVERRIDDEN:DQA_DUPLICATE_UIC(2)" in prov_reasons

    # 3. Changed file hash cancels override (new data uploaded)
    is_blocked, reasons, is_prov = manager.check_export_status(
        dqa_results=sample_dqa_results,
        file_hash="new_different_hash",
        block_on_critical=True,
    )
    assert is_blocked is True
    assert is_prov is False

    # 4. Changed count cancels override
    exceptions_df2 = pd.DataFrame(
        [
            {"rule_id": "DQA_DUPLICATE_UIC", "severity": "Critical", "uic": "UIC-001"},
            {"rule_id": "DQA_DUPLICATE_UIC", "severity": "Critical", "uic": "UIC-002"},
            {"rule_id": "DQA_DUPLICATE_UIC", "severity": "Critical", "uic": "UIC-003"},
        ]
    )
    dqa2 = DQAResults(
        exceptions_df=exceptions_df2,
        summary_df=pd.DataFrame(),
        rule_counts={"DQA_DUPLICATE_UIC": 3},
        severity_counts={"Critical": 3},
        has_critical=True,
        total_exceptions=3,
    )
    is_blocked, reasons, is_prov = manager.check_export_status(
        dqa_results=dqa2,
        file_hash="hash123",
        block_on_critical=True,
    )
    assert is_blocked is True


def test_advisory_mode(temp_audit_log: Path, sample_dqa_results: DQAResults):
    manager = OverrideManager(audit_log_path=temp_audit_log)

    is_blocked, reasons, is_prov = manager.check_export_status(
        dqa_results=sample_dqa_results,
        file_hash="hash123",
        block_on_critical=False,
    )
    assert is_blocked is False
    assert is_prov is True
    assert len(reasons) == 0
    prov = manager.get_provisional_reasons(sample_dqa_results, "hash123", False)
    assert "ADVISORY_MODE:DQA_DUPLICATE_UIC(2)" in prov
