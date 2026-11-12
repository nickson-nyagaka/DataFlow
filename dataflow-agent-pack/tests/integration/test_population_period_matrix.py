"""Full integration test matrix: 5 Populations x 3 Period Modes (15 E2E Pipeline Runs).

Verifies Phase 7 Deliverable:
- Ingestion -> Cleaning -> DQA -> Analytics -> Excel Packaging across all 15 combinations.
- Validates that Master Excel workbook and ZIP archives are generated cleanly without error.
- Asserts population-specific schemas (e.g. PWID has NSP, non-PWID do not).
- Validates total row formulas (=SUM) match independent column sums.
"""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pytest

from core.runner import run_full_pipeline
from reporting.workbook_validator import validate_summary_workbook
from tests.synthetic.generator import generate_synthetic_data

POPULATIONS = ["FSW", "MSM", "PWID", "TG", "VP"]
PERIOD_MODES = ["Q1", "Q2", "SEM"]


@pytest.mark.parametrize("population", POPULATIONS)
@pytest.mark.parametrize("period_mode", PERIOD_MODES)
def test_full_pipeline_population_period_matrix(population: str, period_mode: str, tmp_path: Path):
    """Executes the complete DATAFLOW pipeline across all 15 population x period mode combinations."""
    # 1. Generate compliant synthetic data
    reg_df, kp_df, _ = generate_synthetic_data(population, num_clients=60, seed=100)

    # 2. Build multi-sheet Excel workbook in memory
    wb = openpyxl.Workbook()
    ws_reg = wb.active
    ws_reg.title = "Register"
    ws_reg.append([f"{population} Cohort Register"])
    ws_reg.append([])
    ws_reg.append(list(reg_df.columns))
    for row in reg_df.itertuples(index=False):
        ws_reg.append(list(row))

    ws_kp = wb.create_sheet("KPLHIV")
    ws_kp.append(["KPLHIV Register"])
    ws_kp.append([])
    ws_kp.append(list(kp_df.columns))
    for row in kp_df.itertuples(index=False):
        ws_kp.append(list(row))

    buf = io.BytesIO()
    wb.save(buf)
    file_bytes = buf.getvalue()

    # 3. Execute full pipeline
    result = run_full_pipeline(
        file_source=file_bytes,
        file_name=f"test_{population}_{period_mode}.xlsx",
        population=population,
        period_mode=period_mode,
        force_rerun=True,
    )

    # 4. Verify pipeline bundle
    assert result is not None
    assert result.total_cohort > 0
    assert result.population == population
    assert result.period_mode == period_mode

    # Master workbook & ZIP package verification
    master_path = result.package_paths.get("master_workbook")
    zip_path = result.package_paths.get("zip_package")
    sum_path = result.package_paths.get("summary_workbook")

    assert master_path is not None and master_path.exists()
    assert zip_path is not None and zip_path.exists()
    assert sum_path is not None and sum_path.exists()

    # 5. Programmatic workbook validation (formatting, SUM formulas, visual tokens)
    val_res = validate_summary_workbook(
        file_path=sum_path,
        population=population,
        period_mode=period_mode,
    )
    assert val_res.is_valid is True, f"Validation errors: {val_res.issues}"

    # Verify master workbook contains expected core sheets (Run Metadata & Cleaning Log removed)
    wb_master = openpyxl.load_workbook(master_path, data_only=True)
    ws_sum = wb_master.worksheets[0]
    assert any(k in ws_sum.title for k in ("Summary", "PWID"))
    assert "Run Metadata" not in wb_master.sheetnames
    assert "Cleaning Log" not in wb_master.sheetnames
    assert "DQA Exceptions" in wb_master.sheetnames
    assert "Cleaned Register" in wb_master.sheetnames

    # 6. Verify population-specific block inclusion
    has_nsp = any("NSP" in col.upper() for col in result.summary_df.columns)
    if population == "PWID":
        assert has_nsp is True, "PWID summary must contain NSP block"
    else:
        assert has_nsp is False, f"{population} summary must NOT contain NSP block"
