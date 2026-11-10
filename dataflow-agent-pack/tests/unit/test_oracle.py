"""Unit tests verifying oracle execution on synthetic workbooks (Phase 1)."""

from pathlib import Path

from oracle.runner import run_oracle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "synthetic" / "fixtures"


def test_oracle_runs_end_to_end_on_synthetic_fsw():
    """Runs oracle on synthetic FSW workbook and verifies summary output."""
    wb_path = FIXTURES_DIR / "synthetic_fsw.xlsx"
    assert wb_path.exists(), f"Fixture {wb_path} does not exist"

    results = run_oracle(wb_path, population="FSW")
    summary = results["final_summary"]

    assert not summary.empty
    assert "TotalCohort" in summary.columns
    assert "TotalPE" in summary.columns
    assert "HTSQ1" in summary.columns
    assert "HTSQ2" in summary.columns
    assert "HTS_SEM" in summary.columns
    assert "DefinedPackage_Q1" in summary.columns
    assert "DefinedPackage_Q2" in summary.columns
    assert "DefinedPackage_SEM" in summary.columns
    assert "PREP_SEM" in summary.columns
    assert "Suppressed" in summary.columns


def test_oracle_runs_end_to_end_on_synthetic_pwid():
    """Runs oracle on synthetic PWID workbook and verifies NSP column emission."""
    wb_path = FIXTURES_DIR / "synthetic_pwid.xlsx"
    assert wb_path.exists(), f"Fixture {wb_path} does not exist"

    results = run_oracle(wb_path, population="PWID")
    summary = results["final_summary"]

    assert not summary.empty
    assert "TotalCohort" in summary.columns
    assert "NSP_Q1" in summary.columns
    assert "NSP_Q2" in summary.columns
    assert "NSP_SEM" in summary.columns
    assert "total_nsp_Q1" in summary.columns
    assert "total_nsp_Q2" in summary.columns
