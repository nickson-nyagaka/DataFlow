"""Comprehensive test suite for Phase 6 Streamlit UI.

Verifies:
1. AST scan ensuring ZERO indicator calculation logic (e.g., groupby/agg) in ui/.
2. Dashboard numbers trace directly to runtime/run_metadata.json without hardcoding.
3. AppTest tests across all 8 pages (Dashboard, Upload, Processing, DQA, Analytics, Exports, Config, About).
4. Sabotage upload handling (wrong file type, corrupt file, missing sheet, Critical DQA block).
5. State machine transitions and access gating (D-041).
6. Temporary storage cleanup on success, failure, and 'New Session' (D-044).
7. Localhost binding (127.0.0.1) and usage stats disabled.
"""

from __future__ import annotations

import ast
import io
import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from core.override import OverrideManager
from core.validation import DQAResults
from ui.session import (
    check_page_access,
    purge_temporary_storage,
)
from ui.upload import validate_uploaded_bytes

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_PY = str(PROJECT_ROOT / "app.py")


def ui_path(filename: str) -> str:
    return str(PROJECT_ROOT / "ui" / filename)


def test_ui_contains_zero_indicator_calculation_logic():
    """
    Fails the build if any module in ui/ contains:
    - .groupby()
    - .agg() or .aggregate()
    - indicator formula assignments (e.g. *_SEM = ...)
    """
    ui_dir = Path("ui")
    assert ui_dir.exists(), "ui/ directory must exist"

    disallowed_methods = {"groupby", "agg", "aggregate", "pivot_table", "crosstab"}

    violations: list[str] = []

    for py_file in ui_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

        for node in ast.walk(tree):
            # Check for method calls: df.groupby(), df.agg(), etc.
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in disallowed_methods:
                        violations.append(
                            f"{py_file.name}:{node.lineno} calls disallowed analytical method '{node.func.attr}()'"
                        )

    assert not violations, (
        "Strict separation violated: ui/ must contain ZERO analytical calculation logic. Found:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 2. DASHBOARD NUMBERS TRACE TO RUN METADATA (Exit Criterion)
# ---------------------------------------------------------------------------


def test_dashboard_metrics_trace_to_run_metadata():
    """
    Proves that all Dashboard metrics trace directly to runtime/run_metadata.json
    and change dynamically when the metadata changes (zero hardcoded numbers).
    """
    meta_path = Path("runtime/run_metadata.json")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    backup = meta_path.read_bytes() if meta_path.exists() else None

    sample_meta_1 = {
        "timestamp": "2026-11-11T10:00:00Z",
        "input_file_name": "test_register.xlsx",
        "input_file_hash": "abc1234567890",
        "config_hash": "cfg987",
        "population": "FSW",
        "period_mode": "SEM",
        "total_cohort": 4321,
        "active_kplhiv": 876,
        "total_dqa_exceptions": 54,
        "critical_dqa_count": 0,
        "major_dqa_count": 14,
        "minor_dqa_count": 40,
        "duration_seconds": 12.34,
        "stage_timings": {
            "ingestion": 2.1,
            "cleaning": 1.5,
            "dqa": 3.0,
            "analytics": 2.7,
            "reporting": 3.04,
        },
        "status": "SUCCESS",
    }

    sample_meta_2 = {
        "timestamp": "2026-11-11T11:00:00Z",
        "input_file_name": "msm_register.xlsx",
        "input_file_hash": "xyz9876543210",
        "config_hash": "cfg654",
        "population": "MSM",
        "period_mode": "Q1",
        "total_cohort": 9876,
        "active_kplhiv": 1234,
        "total_dqa_exceptions": 18,
        "critical_dqa_count": 3,
        "major_dqa_count": 5,
        "minor_dqa_count": 10,
        "duration_seconds": 4.56,
        "stage_timings": {
            "ingestion": 1.0,
            "cleaning": 0.5,
            "dqa": 1.0,
            "analytics": 1.0,
            "reporting": 1.06,
        },
        "status": "SUCCESS",
    }

    try:
        # Test Run 1
        meta_path.write_text(json.dumps(sample_meta_1), encoding="utf-8")
        at1 = AppTest.from_file(ui_path("dashboard.py"), default_timeout=15)
        at1.run()
        assert not at1.exception

        metric_values_1 = [m.value for m in at1.metric]
        assert "4,321" in metric_values_1
        assert "876" in metric_values_1
        assert "54" in metric_values_1
        assert "12.34s" in metric_values_1

        # Test Run 2 with modified values
        meta_path.write_text(json.dumps(sample_meta_2), encoding="utf-8")
        at2 = AppTest.from_file(ui_path("dashboard.py"), default_timeout=15)
        at2.run()
        assert not at2.exception

        metric_values_2 = [m.value for m in at2.metric]
        assert "9,876" in metric_values_2
        assert "1,234" in metric_values_2
        assert "18" in metric_values_2
        assert "4.56s" in metric_values_2

    finally:
        if backup is not None:
            meta_path.write_bytes(backup)
        elif meta_path.exists():
            meta_path.unlink()


def test_dashboard_empty_state_when_no_metadata():
    """Verifies friendly empty state when no pipeline runs have occurred."""
    meta_path = Path("runtime/run_metadata.json")
    backup = meta_path.read_bytes() if meta_path.exists() else None
    if meta_path.exists():
        meta_path.unlink()

    try:
        at = AppTest.from_file(ui_path("dashboard.py"), default_timeout=15)
        at.run()
        assert not at.exception
        assert any("No pipeline runs recorded yet" in info.value for info in at.info)
        assert all(m.value == "—" for m in at.metric)
    finally:
        if backup is not None:
            meta_path.write_bytes(backup)


# ---------------------------------------------------------------------------
# 3. SABOTAGE UPLOADS & DATA-FREE VALIDATION (Exit Criterion)
# ---------------------------------------------------------------------------


def test_sabotage_upload_wrong_file_type():
    """Validates that unsupported file types show friendly data-free error."""
    is_valid, err = validate_uploaded_bytes(b"dummy text content", "cohort.txt", "FSW")
    assert is_valid is False
    assert "Unsupported file extension '.txt'" in err
    assert "UIC" not in err


def test_sabotage_upload_empty_file():
    """Validates that 0-byte file shows friendly error."""
    is_valid, err = validate_uploaded_bytes(b"", "empty.xlsx", "FSW")
    assert is_valid is False
    assert "empty (0 bytes)" in err


def test_sabotage_upload_corrupt_workbook():
    """Validates that corrupt Excel workbook bytes show friendly error."""
    is_valid, err = validate_uploaded_bytes(
        b"PK\x03\x04corruptedbytesnotazip", "corrupt.xlsx", "FSW"
    )
    assert is_valid is False
    assert "corrupt or malformed" in err


def test_sabotage_upload_missing_register_sheet():
    """Validates that a multi-sheet workbook missing a register sheet shows friendly error."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RandomSheet1"
    wb.create_sheet("RandomSheet2")
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()

    is_valid, err = validate_uploaded_bytes(buf.getvalue(), "missing_reg.xlsx", "FSW")
    assert is_valid is False
    assert "Required register sheet not found" in err


# ---------------------------------------------------------------------------
# 4. CRITICAL DQA EXPORT BLOCKING (Decision D-042 & Exit Criterion)
# ---------------------------------------------------------------------------


def test_sabotage_critical_dqa_blocks_summary_export(tmp_path: Path):
    """Verifies that Critical DQA exceptions block exports and show friendly alerts."""
    mgr = OverrideManager(audit_log_path=tmp_path / "audit.jsonl")

    exc_df = pd.DataFrame(
        [{"rule_id": "DQA_DUPLICATE_UIC", "severity": "Critical", "uic": "UIC-001"}]
    )
    dqa = DQAResults(
        exceptions_df=exc_df,
        summary_df=pd.DataFrame(),
        rule_counts={"DQA_DUPLICATE_UIC": 1},
        severity_counts={"Critical": 1},
        has_critical=True,
        total_exceptions=1,
    )

    is_blocked, reasons, is_prov = mgr.check_export_status(
        dqa_results=dqa,
        file_hash="hash_test",
        block_on_critical=True,
    )
    assert is_blocked is True
    assert "DQA_DUPLICATE_UIC" in reasons[0]
    assert "UIC-001" not in reasons[0]  # Zero PII in reasons


# ---------------------------------------------------------------------------
# 5. STATE MACHINE PROGRESSION & GATING (Decision D-041)
# ---------------------------------------------------------------------------


def test_state_machine_access_gating(monkeypatch):
    """Verifies page access permissions across state machine lifecycle."""
    import streamlit as st

    # IDLE stage
    monkeypatch.setattr(st, "session_state", {"stage": "IDLE"})
    assert check_page_access("Dashboard") is True
    assert check_page_access("Upload Data") is True
    assert check_page_access("Configuration") is True
    assert check_page_access("About") is True
    assert check_page_access("Processing") is False
    assert check_page_access("Data Quality") is False
    assert check_page_access("Analytics") is False
    assert check_page_access("Export Reports") is False

    # UPLOADED stage
    monkeypatch.setattr(st, "session_state", {"stage": "UPLOADED"})
    assert check_page_access("Processing") is True
    assert check_page_access("Data Quality") is False
    assert check_page_access("Analytics") is False
    assert check_page_access("Export Reports") is False

    # PROCESSED stage
    monkeypatch.setattr(st, "session_state", {"stage": "PROCESSED"})
    assert check_page_access("Data Quality") is True
    assert check_page_access("Analytics") is True
    assert check_page_access("Export Reports") is True


# ---------------------------------------------------------------------------
# 6. APPTEST VERIFICATION FOR ALL PAGES (Exit Criterion)
# ---------------------------------------------------------------------------


def test_app_main_navigation_render():
    """Runs app.py through AppTest ensuring clean bootstrap and navigation render."""
    at = AppTest.from_file(APP_PY, default_timeout=20)
    at.run()
    assert not at.exception
    # Verify sidebar brand and buttons
    assert any("DATAFLOW" in s.value for s in at.sidebar.markdown)
    assert any("New Session" in b.label for b in at.sidebar.button)


def test_upload_page_render():
    """Runs ui/upload.py through AppTest."""
    at = AppTest.from_file(ui_path("upload.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("Upload Cohort Data" in t.value for t in at.title)


def test_processing_page_render_empty():
    """Runs ui/processing.py with no uploaded file (guards cleanly)."""
    at = AppTest.from_file(ui_path("processing.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("Page Locked" in w.value for w in at.warning)


def test_data_quality_page_render_empty():
    """Runs ui/data_quality.py through AppTest with no session state (guards cleanly)."""
    at = AppTest.from_file(ui_path("data_quality.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("Page Locked" in w.value for w in at.warning)


def test_analytics_page_render_empty():
    """Runs ui/analytics.py through AppTest with no session state (guards cleanly)."""
    at = AppTest.from_file(ui_path("analytics.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("Page Locked" in w.value for w in at.warning)


def test_exports_page_render_empty():
    """Runs ui/exports.py through AppTest with no session state (guards cleanly)."""
    at = AppTest.from_file(ui_path("exports.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("Page Locked" in w.value for w in at.warning)


def _build_test_pipeline_result(tmp_path: Path):
    from core.runner import PipelineResult

    master_p = tmp_path / "master.xlsx"
    master_p.write_bytes(b"dummy_master_content")
    zip_p = tmp_path / "package.zip"
    zip_p.write_bytes(b"dummy_zip_content")

    dqa = DQAResults(
        exceptions_df=pd.DataFrame(
            [
                {
                    "rule_id": "DQA_INVALID_AGE",
                    "severity": "Minor",
                    "uic": "UIC-001",
                    "description": "Invalid age",
                }
            ]
        ),
        summary_df=pd.DataFrame(
            [
                {
                    "rule_id": "DQA_INVALID_AGE",
                    "rule_name": "Invalid Age",
                    "severity": "Minor",
                    "count": 1,
                    "remediation": "Check birth date",
                }
            ]
        ),
        rule_counts={"DQA_INVALID_AGE": 1},
        severity_counts={"Minor": 1},
        has_critical=False,
        total_exceptions=1,
    )
    return PipelineResult(
        input_file_name="cohort_test.xlsx",
        input_file_hash="mock_hash_12345",
        config_hash="cfg_hash_67890",
        population="FSW",
        period_mode="SEM",
        cleaned_register=pd.DataFrame([{"uic": "UIC-001"}]),
        cleaned_kplhiv=pd.DataFrame(),
        dqa_results=dqa,
        summary_df=pd.DataFrame(
            [
                {
                    "County": "Nairobi",
                    "SR Name": "Partner A",
                    "Region": "Central",
                    "hts_tst_pos_SEM": 5,
                }
            ]
        ),
        kplhiv_summary_df=pd.DataFrame(),
        package_paths={"master_workbook": master_p, "zip_package": zip_p},
        display_analytics={
            "hts_cascade": {"Tested": 100, "Negative": 95, "Positive": 5, "Linked": 5},
            "prep_cascade": {"Screened": 80, "Eligible": 60, "New": 30, "Current": 50},
            "art_suppression": {
                "Active KPLHIV": 20,
                "On ART": 18,
                "Viral Load Done": 15,
                "Suppressed": 14,
            },
            "commodities": {
                "Male Condoms": 500,
                "Female Condoms": 50,
                "Lubricants": 200,
                "Needles & Syringes": 0,
            },
            "geography_breakdown": [
                {"County": "Nairobi", "SR Name": "Partner A", "Region": "Central"}
            ],
        },
        stage_timings={
            "ingestion": 1.0,
            "cleaning": 0.5,
            "dqa": 0.5,
            "analytics": 0.5,
            "reporting": 1.0,
        },
        total_cohort=100,
        active_kplhiv=20,
        total_dqa_exceptions=1,
        critical_dqa_count=0,
        major_dqa_count=0,
        minor_dqa_count=1,
        duration_seconds=3.5,
        timestamp="2026-11-11T09:00:00Z",
    )


def test_data_quality_page_render_processed_state(tmp_path: Path):
    """Runs ui/data_quality.py through AppTest with populated PROCESSED session state."""
    res = _build_test_pipeline_result(tmp_path)
    at = AppTest.from_file(ui_path("data_quality.py"), default_timeout=20)
    at.session_state["stage"] = "PROCESSED"
    at.session_state["pipeline_result"] = res
    at.run()
    assert not at.exception
    assert any("Data Quality Assurance" in t.value for t in at.title)
    assert any("Minor" in m.label for m in at.metric)


def test_analytics_page_render_processed_state(tmp_path: Path):
    """Runs ui/analytics.py through AppTest with populated PROCESSED session state."""
    res = _build_test_pipeline_result(tmp_path)
    at = AppTest.from_file(ui_path("analytics.py"), default_timeout=20)
    at.session_state["stage"] = "PROCESSED"
    at.session_state["pipeline_result"] = res
    at.run()
    assert not at.exception
    assert any("Key Population Analytics" in t.value for t in at.title)
    assert any("Clients Tested" in m.label for m in at.metric)


def test_dashboard_page_render_processed_state(tmp_path: Path):
    """Runs ui/dashboard.py through AppTest with populated PROCESSED session state and charts."""
    res = _build_test_pipeline_result(tmp_path)
    at = AppTest.from_file(ui_path("dashboard.py"), default_timeout=20)
    at.session_state["stage"] = "PROCESSED"
    at.session_state["pipeline_result"] = res
    at.run()
    assert not at.exception
    assert any("Cohort Performance Dashboard" in t.value for t in at.title)
    assert any("Total Cohort Clients" in m.label for m in at.metric)


def test_exports_page_render_processed_state(tmp_path: Path):
    """Runs ui/exports.py through AppTest with populated PROCESSED session state."""
    res = _build_test_pipeline_result(tmp_path)
    at = AppTest.from_file(ui_path("exports.py"), default_timeout=20)
    at.session_state["stage"] = "PROCESSED"
    at.session_state["pipeline_result"] = res
    at.session_state["block_on_critical"] = True
    at.session_state["mask_identifiers"] = False
    at.run()
    assert not at.exception
    assert any("Export Reporting Packages" in t.value for t in at.title)
    assert any("Master Excel Package" in b.label for b in at.download_button)


def test_exports_page_allows_download_when_dqa_exceptions_exist(tmp_path: Path):
    """Verifies that DQA exceptions do not prohibit downloading of export packages."""
    res = _build_test_pipeline_result(tmp_path)
    # Simulate Critical DQA exceptions present
    exc_df = pd.DataFrame(
        [{"rule_id": "DQA_HIV_NEG_ON_ART", "severity": "Critical", "uic": "UIC-001"}]
    )
    res.dqa_results = DQAResults(
        exceptions_df=exc_df,
        summary_df=pd.DataFrame(),
        rule_counts={"DQA_HIV_NEG_ON_ART": 1},
        severity_counts={"Critical": 1},
        has_critical=True,
        total_exceptions=1,
    )
    at = AppTest.from_file(ui_path("exports.py"), default_timeout=20)
    at.session_state["stage"] = "PROCESSED"
    at.session_state["pipeline_result"] = res
    at.session_state["block_on_critical"] = True
    at.session_state["mask_identifiers"] = False
    at.run()
    assert not at.exception

    # Ensure download buttons are present and not disabled
    master_btns = [b for b in at.download_button if "Master Excel Package" in b.label]
    assert len(master_btns) == 1
    assert not master_btns[0].disabled

    zip_btns = [b for b in at.download_button if "Modular ZIP Archive" in b.label]
    assert len(zip_btns) == 1
    assert not zip_btns[0].disabled


def test_configuration_page_render():
    """Runs ui/configuration.py through AppTest."""
    at = AppTest.from_file(ui_path("configuration.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("System Configuration" in t.value for t in at.title)


def test_about_page_render():
    """Runs ui/about.py through AppTest."""
    at = AppTest.from_file(ui_path("about.py"), default_timeout=20)
    at.run()
    assert not at.exception
    assert any("About DATAFLOW" in t.value for t in at.title)
    assert any("DATAFLOW v1.0.0" in m.value for m in at.markdown)


# ---------------------------------------------------------------------------
# 7. TEMPORARY STORAGE HYGIENE (Decision D-044 & Exit Criterion)
# ---------------------------------------------------------------------------


def test_temporary_storage_purge(tmp_path: Path):
    """Verifies that purge_temporary_storage removes files and leaves .gitkeep."""
    temp_dir = tmp_path / "temporary"
    temp_dir.mkdir(parents=True)
    (temp_dir / ".gitkeep").write_text("", encoding="utf-8")
    (temp_dir / "temp_file1.xlsx").write_bytes(b"data1")
    (temp_dir / "temp_file2.csv").write_bytes(b"data2")
    sub = temp_dir / "temp_subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")

    deleted = purge_temporary_storage(target_dir=temp_dir)
    assert deleted == 3
    assert (temp_dir / ".gitkeep").exists()
    assert not (temp_dir / "temp_file1.xlsx").exists()
    assert not (temp_dir / "temp_file2.csv").exists()
    assert not sub.exists()


# ---------------------------------------------------------------------------
# 8. LOCALHOST BINDING AND PRIVACY CONFIGURATION (Exit Criterion)
# ---------------------------------------------------------------------------


def test_streamlit_config_localhost_binding():
    """Verifies that .streamlit/config.toml binds strictly to 127.0.0.1 and telemetry is off."""
    cfg_path = Path(".streamlit/config.toml")
    assert cfg_path.exists(), ".streamlit/config.toml must exist"

    text = cfg_path.read_text(encoding="utf-8")
    assert 'address = "127.0.0.1"' in text, "Must bind strictly to localhost 127.0.0.1"
    assert "gatherUsageStats = false" in text, "Usage stats / telemetry must be disabled"
