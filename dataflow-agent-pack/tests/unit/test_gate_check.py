"""Unit tests for scripts/gate_check.py (Phase 1).

Verifies phase-gate enforcement:
1. Contiguous approval validation.
2. Rejection of out-of-sequence work.
3. Detection of tampered approval files (duplicate phases, missing phases, non-contiguous approvals).
"""

from pathlib import Path

import pytest

from scripts.gate_check import current_phase, main, read_statuses


def _create_mock_gate_file(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "PHASE_APPROVALS.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_gate_check_normal_allowed_phase(tmp_path):
    """Verifies that when Phase 0 is APPROVED and Phase 1 is PENDING, current phase is 1."""
    content = [
        "# Approvals",
        "PHASE 0 | STATUS: APPROVED | by: Nickson | date: 2026-11-10 | tag: phase-0-submitted",
        "PHASE 1 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 2 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 3 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 4 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 5 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 6 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 7 | STATUS: PENDING | by: - | date: - | tag: -",
    ]
    gate_file = _create_mock_gate_file(tmp_path, content)
    statuses = read_statuses(gate_file)
    assert statuses[0] == "APPROVED"
    assert statuses[1] == "PENDING"
    assert current_phase(statuses) == 1


def test_gate_check_rejects_out_of_sequence_work(monkeypatch, tmp_path, capsys):
    """Proves gate_check rejects asking for Phase 2 when only Phase 1 is allowed."""
    content = [
        "PHASE 0 | STATUS: APPROVED | by: Nickson | date: 2026-11-10 | tag: phase-0-submitted",
        "PHASE 1 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 2 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 3 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 4 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 5 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 6 | STATUS: PENDING | by: - | date: - | tag: -",
        "PHASE 7 | STATUS: PENDING | by: - | date: - | tag: -",
    ]
    gate_file = _create_mock_gate_file(tmp_path, content)
    monkeypatch.setattr("scripts.gate_check.GATE_FILE", gate_file)

    # Calling gate_check with Phase 2 should exit with code 1 (BLOCKED)
    ret = main(["gate_check.py", "2"])
    assert ret == 1
    captured = capsys.readouterr().out
    assert "BLOCKED: phase 2 is not allowed" in captured
    assert "The only allowed phase is 1" in captured

    # Calling gate_check with Phase 1 should return 0 (OK)
    ret_ok = main(["gate_check.py", "1"])
    assert ret_ok == 0
    captured_ok = capsys.readouterr().out
    assert "OK: phase 1 is the allowed phase" in captured_ok


def test_gate_check_detects_non_contiguous_approvals(tmp_path):
    """Proves gate_check detects tampered file where Phase 2 is APPROVED but Phase 1 is PENDING."""
    content = [
        "PHASE 0 | STATUS: APPROVED",
        "PHASE 1 | STATUS: PENDING",
        "PHASE 2 | STATUS: APPROVED",  # Non-contiguous!
        "PHASE 3 | STATUS: PENDING",
        "PHASE 4 | STATUS: PENDING",
        "PHASE 5 | STATUS: PENDING",
        "PHASE 6 | STATUS: PENDING",
        "PHASE 7 | STATUS: PENDING",
    ]
    gate_file = _create_mock_gate_file(tmp_path, content)
    statuses = read_statuses(gate_file)
    with pytest.raises(SystemExit) as exc_info:
        current_phase(statuses)
    assert "phase 2 is APPROVED but an earlier phase is not" in str(exc_info.value)


def test_gate_check_detects_duplicate_phase(tmp_path):
    """Proves gate_check detects duplicate phase line in approvals file."""
    content = [
        "PHASE 0 | STATUS: APPROVED",
        "PHASE 1 | STATUS: PENDING",
        "PHASE 1 | STATUS: APPROVED",  # Duplicate!
        "PHASE 2 | STATUS: PENDING",
        "PHASE 3 | STATUS: PENDING",
        "PHASE 4 | STATUS: PENDING",
        "PHASE 5 | STATUS: PENDING",
        "PHASE 6 | STATUS: PENDING",
        "PHASE 7 | STATUS: PENDING",
    ]
    gate_file = _create_mock_gate_file(tmp_path, content)
    with pytest.raises(SystemExit) as exc_info:
        read_statuses(gate_file)
    assert "phase 1 appears more than once" in str(exc_info.value)


def test_gate_check_detects_missing_phase(tmp_path):
    """Proves gate_check detects missing phase line in approvals file."""
    content = [
        "PHASE 0 | STATUS: APPROVED",
        "PHASE 1 | STATUS: PENDING",
        # PHASE 2 is missing!
        "PHASE 3 | STATUS: PENDING",
        "PHASE 4 | STATUS: PENDING",
        "PHASE 5 | STATUS: PENDING",
        "PHASE 6 | STATUS: PENDING",
        "PHASE 7 | STATUS: PENDING",
    ]
    gate_file = _create_mock_gate_file(tmp_path, content)
    with pytest.raises(SystemExit) as exc_info:
        read_statuses(gate_file)
    assert "missing phase line(s): [2]" in str(exc_info.value)


def test_gate_check_missing_file():
    """Proves gate_check halts if approvals file does not exist."""
    non_existent = Path("non/existent/path/PHASE_APPROVALS.md")
    with pytest.raises(SystemExit) as exc_info:
        read_statuses(non_existent)
    assert "not found. Stop and tell the Owner." in str(exc_info.value)


def test_gate_check_rejected_phase_guidance(monkeypatch, tmp_path, capsys):
    """Proves gate_check outputs rejection guidance when phase is REJECTED."""
    content = [
        "PHASE 0 | STATUS: APPROVED",
        "PHASE 1 | STATUS: REJECTED",
        "PHASE 2 | STATUS: PENDING",
        "PHASE 3 | STATUS: PENDING",
        "PHASE 4 | STATUS: PENDING",
        "PHASE 5 | STATUS: PENDING",
        "PHASE 6 | STATUS: PENDING",
        "PHASE 7 | STATUS: PENDING",
    ]
    gate_file = _create_mock_gate_file(tmp_path, content)
    monkeypatch.setattr("scripts.gate_check.GATE_FILE", gate_file)

    ret = main(["gate_check.py"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert (
        "ALLOWED PHASE: 1 (REJECTED: rework only the defects in docs/gates/REJECTIONS.md)"
        in captured
    )
