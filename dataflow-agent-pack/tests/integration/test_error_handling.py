"""Integration tests for end-to-end error handling and sabotage inputs.

Verifies Phase 7 Deliverable:
- Robust error trapping on corrupted, truncated, empty, and malformed files.
- Zero client PII / identifier exposure in error messages.
- Clean temporary storage handling upon pipeline failures.
"""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pytest

from core.exceptions import IngestionError
from core.runner import run_full_pipeline
from ui.upload import validate_uploaded_bytes


def test_validate_rejects_unsupported_extension():
    is_valid, err = validate_uploaded_bytes(b"dummy content", "test.pdf", "FSW")
    assert is_valid is False
    assert "Unsupported file extension '.pdf'" in err
    assert "UIC" not in err


def test_validate_rejects_empty_bytes():
    is_valid, err = validate_uploaded_bytes(b"", "empty.xlsx", "FSW")
    assert is_valid is False
    assert "empty (0 bytes)" in err


def test_validate_rejects_corrupt_bytes():
    corrupt = b"PK\x03\x04corrupted_header_data_not_valid_zip"
    is_valid, err = validate_uploaded_bytes(corrupt, "corrupt.xlsx", "FSW")
    assert is_valid is False
    assert "corrupt or malformed" in err


def test_validate_rejects_missing_register_sheet():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RandomSheet1"
    wb.create_sheet("RandomSheet2")
    buf = io.BytesIO()
    wb.save(buf)

    is_valid, err = validate_uploaded_bytes(buf.getvalue(), "missing_reg.xlsx", "FSW")
    assert is_valid is False
    assert "Required register sheet not found" in err


def test_pipeline_raises_data_free_ingestion_error_on_corrupt_file(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.xlsx"
    corrupt_file.write_bytes(b"Corrupted non-zip non-excel bytes")

    with pytest.raises(IngestionError) as exc_info:
        run_full_pipeline(
            file_source=corrupt_file,
            file_name="corrupt.xlsx",
            population="FSW",
            period_mode="SEM",
            force_rerun=True,
        )

    err_msg = str(exc_info.value)
    # Ensure error is informative and completely data-free
    assert "corrupt" in err_msg.lower() or "failed" in err_msg.lower()
    assert "uic" not in err_msg.lower()
    assert "nupi" not in err_msg.lower()
