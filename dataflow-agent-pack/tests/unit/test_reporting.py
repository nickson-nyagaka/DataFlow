"""Unit tests for Phase 5 reporting package: templates, exporters, summaries, and validators."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import pytest

from core.compat import CompatSwitches
from reporting.cleaned_data_exporter import (
    apply_identifier_masking,
    export_cleaned_data_workbook,
    mask_identifier,
)
from reporting.dqa_exporter import export_dqa_exceptions_workbook
from reporting.excel_exporter import (
    export_summary_workbook,
)
from reporting.package_builder import build_reporting_package
from reporting.summary_builder import build_export_summary
from reporting.template_manager import get_template_manager
from reporting.workbook_validator import validate_summary_workbook
from tests.synthetic.generator import generate_synthetic_data


@pytest.fixture
def sample_synthetic_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generates a small deterministic synthetic dataset for testing."""
    fsw_reg, fsw_kp, _ = generate_synthetic_data(population="FSW", num_clients=50, seed=42)
    return fsw_reg, fsw_kp


@pytest.fixture
def pwid_synthetic_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generates synthetic PWID dataset for testing."""
    pwid_reg, pwid_kp, _ = generate_synthetic_data(population="PWID", num_clients=50, seed=42)
    return pwid_reg, pwid_kp


def test_template_config_loading() -> None:
    """Verifies that excel_templates.yaml loads completely with all layouts and styling tokens."""
    config = get_template_manager()
    assert config.fonts.header == "Cascadia Code"
    assert config.fonts.body == "Candara"
    assert config.fills.subheader == "FF7D81"
    assert config.fills.total == "6BD669"

    # Check layouts
    assert "semester_standard" in config.layouts
    assert "semester_pwid" in config.layouts
    assert "q1_standard" in config.layouts
    assert "q1_pwid" in config.layouts

    # Exact column counts per layout specification
    assert config.get_layout("semester_standard").total_columns == 50
    assert config.get_layout("semester_pwid").total_columns == 56
    assert config.get_layout("q1_standard").total_columns == 25
    assert config.get_layout("q1_pwid").total_columns == 27


def test_layout_resolution() -> None:
    """Tests resolution of layout spec and sheet name by population and period mode."""
    config = get_template_manager()

    # Sheet names per notebook audit
    assert config.get_sheet_name_for("FSW", "SEM") == "Summary"
    assert config.get_sheet_name_for("MSM", "SEM") == "Summary"
    assert config.get_sheet_name_for("PWID", "SEM") == "PWID_Summary"
    assert config.get_sheet_name_for("FSW", "Q1") == "KP_Summary"
    assert config.get_sheet_name_for("PWID", "Q1") == "PWID_Summary"

    # Layout specs
    assert config.get_layout_for("FSW", "SEM").name == "semester_standard"
    assert config.get_layout_for("PWID", "SEM").name == "semester_pwid"
    assert config.get_layout_for("MSM", "Q1").name == "q1_standard"
    assert config.get_layout_for("PWID", "Q1").name == "q1_pwid"


def test_missing_geography_rows_retained(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies that records with missing geography are NOT dropped, emitting explicit (MISSING) rows."""
    reg_df, kp_df = sample_synthetic_data
    # Plant missing geography in 3 rows
    reg_df = reg_df.copy()
    reg_df.loc[0:2, "county"] = np.nan
    reg_df.loc[3:4, "sr_name"] = None

    summary = build_export_summary(reg_df, kp_df, population="FSW", period_mode="SEM")
    assert not summary.empty
    assert "(MISSING)" in summary["county"].values
    assert "(MISSING)" in summary["sr_name"].values

    # Check TotalCohort sum equals unique UICs in register
    total_uics = reg_df["kp_vp_unique_identifier_code"].nunique()
    assert summary["TotalCohort"].sum() == total_uics


def test_hierarchical_sorting_with_missing_at_bottom() -> None:
    """Verifies D-037: County -> SR Name -> Region with (MISSING) placed at the bottom."""
    reg_df = pd.DataFrame(
        {
            "county": ["Nairobi", None, "Mombasa", "Kisumu"],
            "sr_name": ["SR A", "SR B", "SR A", "SR C"],
            "region": ["Central", "Coast", "Coast", "West"],
            "kp_vp_unique_identifier_code": ["U1", "U2", "U3", "U4"],
            "peer_educator_code": ["PE1", "PE2", "PE3", "PE4"],
            "age": [20, 25, 30, 18],
        }
    )
    kp_df = pd.DataFrame(columns=["county", "sr_name", "region", "kp_vp_unique_identifier_code"])

    summary = build_export_summary(reg_df, kp_df, population="FSW", period_mode="SEM")
    assert summary["county"].iloc[-1] == "(MISSING)"
    assert list(summary["county"].iloc[:-1]) == ["Kisumu", "Mombasa", "Nairobi"]


def test_pwid_total_nsp_sem_calculated(
    pwid_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies D-032: total_nsp_SEM = total_nsp_Q1 + total_nsp_Q2 in PWID reports."""
    reg_df, kp_df = pwid_synthetic_data
    summary = build_export_summary(reg_df, kp_df, population="PWID", period_mode="SEM")

    assert "total_nsp_SEM" in summary.columns
    assert "total_nsp_Q1" in summary.columns
    assert "total_nsp_Q2" in summary.columns

    # Verify column equality
    expected_sum = summary["total_nsp_Q1"] + summary["total_nsp_Q2"]
    pd.testing.assert_series_equal(summary["total_nsp_SEM"], expected_sum, check_names=False)


def test_excel_export_visual_formatting(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Validates Cascadia Code headers, Candara body, fills, freeze panes, and formulas."""
    reg_df, kp_df = sample_synthetic_data
    summary = build_export_summary(reg_df, kp_df, population="FSW", period_mode="SEM")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test_summary.xlsx"
        export_summary_workbook(summary, population="FSW", period_mode="SEM", output_path=out_path)

        assert out_path.is_file()

        # Reopen with openpyxl
        wb = openpyxl.load_workbook(out_path, data_only=False)
        assert "Summary" in wb.sheetnames
        ws = wb["Summary"]

        # View settings
        assert ws.freeze_panes == "A3"
        assert ws.sheet_view.showGridLines is False
        assert ws.row_dimensions[1].height == 22
        assert ws.row_dimensions[2].height == 30
        assert ws.column_dimensions["A"].width == 22
        assert ws.column_dimensions["D"].width == 14

        # Header fonts
        assert ws["A1"].font.name == "Cascadia Code"
        assert ws["A1"].font.bold is True
        assert ws["A2"].font.name == "Cascadia Code"

        # Subheader fill (coral FF7D81)
        r2_color = str(ws["A2"].fill.start_color.rgb)
        if len(r2_color) == 8 and r2_color.startswith("00"):
            r2_color = r2_color[2:]
        assert r2_color.upper() == "FF7D81"

        # Total row
        last_row = ws.max_row
        assert ws.cell(row=last_row, column=1).value == "TOTAL"
        tot_color = str(ws.cell(row=last_row, column=1).fill.start_color.rgb)
        if len(tot_color) == 8 and tot_color.startswith("00"):
            tot_color = tot_color[2:]
        assert tot_color.upper() == "6BD669"

        # Formula check
        tot_formula = ws.cell(row=last_row, column=4).value
        assert str(tot_formula).startswith("=SUM(D3:D")


def test_workbook_validator(sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    """Verifies that validate_summary_workbook passes on valid export and catches corruptions."""
    reg_df, kp_df = sample_synthetic_data
    summary = build_export_summary(reg_df, kp_df, population="FSW", period_mode="SEM")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "valid_summary.xlsx"
        export_summary_workbook(summary, population="FSW", period_mode="SEM", output_path=out_path)

        res = validate_summary_workbook(
            file_path=out_path,
            population="FSW",
            period_mode="SEM",
            reference_df=summary,
        )
        assert res.is_valid is True
        assert len(res.issues) == 0
        assert res.formula_checks_passed > 0
        assert res.formula_checks_failed == 0


def test_pwid_vs_non_pwid_nsp_block(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
    pwid_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies NSP block is strictly present in PWID and absent in Non-PWID."""
    fsw_reg, fsw_kp = sample_synthetic_data
    pwid_reg, pwid_kp = pwid_synthetic_data

    fsw_summary = build_export_summary(fsw_reg, fsw_kp, population="FSW", period_mode="SEM")
    pwid_summary = build_export_summary(pwid_reg, pwid_kp, population="PWID", period_mode="SEM")

    assert "NSP_Q1" in pwid_summary.columns
    assert "total_nsp_SEM" in pwid_summary.columns

    assert "NSP_Q1" not in fsw_summary.columns
    assert "total_nsp_SEM" not in fsw_summary.columns


def test_dqa_exceptions_empty_table_formatting() -> None:
    """Verifies D-034: Clean register emits standard 7-column headers with informational banner."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "dqa_clean.xlsx"
        export_dqa_exceptions_workbook(None, output_path=out_path)

        wb = openpyxl.load_workbook(out_path)
        ws = wb["DQA_Exceptions"]

        # Row 1 has 7 headers
        headers = [ws.cell(row=1, column=c).value for c in range(1, 8)]
        assert headers == [
            "Rule ID",
            "Severity",
            "UIC",
            "County",
            "Sub-Recipient",
            "Offending Columns",
            "Suggested Action",
        ]

        # Row 2 contains informational banner
        banner_val = str(ws.cell(row=2, column=1).value)
        assert "No data quality exceptions detected" in banner_val


def test_identifier_masking() -> None:
    """Verifies D-035: Deterministic salted pseudo-hash MASK-XXXX masking."""
    raw_uic = "FSW-1002-2024"
    masked1 = mask_identifier(raw_uic)
    masked2 = mask_identifier(raw_uic)

    assert masked1.startswith("MASK-")
    assert len(masked1) == 11  # MASK- + 6 hex chars
    assert masked1 == masked2  # Deterministic

    # Test DataFrame masking
    df = pd.DataFrame(
        {
            "kp_vp_unique_identifier_code": [raw_uic, "FSW-9999"],
            "county": ["Nairobi", "Mombasa"],
            "ccc_number": ["1234567890", "0987654321"],
        }
    )
    masked_df = apply_identifier_masking(df)
    assert not masked_df["kp_vp_unique_identifier_code"].str.contains("FSW").any()
    assert masked_df["kp_vp_unique_identifier_code"].str.startswith("MASK-").all()
    assert masked_df["county"].iloc[0] == "Nairobi"  # Non-identifier preserved


def test_reporting_package_builder_multi_tab_and_zip(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies build_reporting_package creates master multi-tab workbook and valid ZIP package."""
    reg_df, kp_df = sample_synthetic_data

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = build_reporting_package(
            cleaned_register=reg_df,
            cleaned_kplhiv=kp_df,
            population="FSW",
            period_mode="SEM",
            output_dir=tmpdir,
            input_file_hash="test_sha256",
            config_hash="test_cfg_hash",
        )

        master_path = pkg["master_workbook"]
        zip_path = pkg["zip_package"]

        assert master_path.is_file()
        assert zip_path.is_file()

        # Validate Master Workbook has all 6 tabs
        wb = openpyxl.load_workbook(master_path, data_only=False)
        expected_tabs = [
            "Summary",
            "Cleaned Register",
            "Cleaned KPLHIV",
            "DQA Exceptions",
            "Run Metadata",
            "Cleaning Log",
        ]
        for tab in expected_tabs:
            assert tab in wb.sheetnames, f"Tab '{tab}' missing in master workbook"

        # Check Run Metadata tab contains confidentiality notice per D-031
        meta_ws = wb["Run Metadata"]
        found_notice = False
        for r in range(1, meta_ws.max_row + 1):
            cell_val = str(meta_ws.cell(row=r, column=1).value)
            if "CONFIDENTIAL MEDICAL INFORMATION" in cell_val:
                found_notice = True
                break
        assert found_notice is True

        # Validate ZIP Archive
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert master_path.name in namelist
            assert "01_Summary_FSW_SEM.xlsx" in namelist
            assert "02_Cleaned_Data_FSW.xlsx" in namelist
            assert "03_DQA_Exceptions_FSW.xlsx" in namelist


def test_all_five_populations_reopen_and_validate() -> None:
    """Verifies exit criterion: All 5 population packages build, reopen, and validate successfully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for pop in ["FSW", "MSM", "PWID", "TG", "VP"]:
            reg_df, kp_df, _ = generate_synthetic_data(population=pop, num_clients=30, seed=123)
            pkg = build_reporting_package(
                cleaned_register=reg_df,
                cleaned_kplhiv=kp_df,
                population=pop,
                period_mode="SEM",
                output_dir=tmpdir,
            )

            # Reopen and validate master workbook
            val_res = validate_summary_workbook(
                file_path=pkg["master_workbook"],
                population=pop,
                period_mode="SEM",
            )
            assert val_res.is_valid is True, f"Validation failed for {pop}: {val_res.issues}"


def test_compare_summaries_script(sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    """Verifies that compare_summaries detects matching workbooks and identifies deltas."""
    from scripts.compare_summaries import compare_summary_workbooks

    reg_df, kp_df = sample_synthetic_data
    summary1 = build_export_summary(reg_df, kp_df, population="FSW", period_mode="SEM")
    summary2 = summary1.copy()

    with tempfile.TemporaryDirectory() as tmpdir:
        path1 = Path(tmpdir) / "fsw_1.xlsx"
        path2 = Path(tmpdir) / "fsw_2.xlsx"
        path3 = Path(tmpdir) / "fsw_3.xlsx"

        export_summary_workbook(summary1, population="FSW", period_mode="SEM", output_path=path1)
        export_summary_workbook(summary2, population="FSW", period_mode="SEM", output_path=path2)

        # Modify summary2 for path3
        summary2.iloc[0, 4] = 99999
        export_summary_workbook(summary2, population="FSW", period_mode="SEM", output_path=path3)

        # Compare identical
        res_same = compare_summary_workbooks(path1, path2)
        assert res_same["identical"] is True
        assert res_same["sheet_comparisons"]["Summary"]["differing_cells"] == 0

        # Compare different
        res_diff = compare_summary_workbooks(path1, path3)
        assert res_diff["identical"] is False
        assert res_diff["sheet_comparisons"]["Summary"]["differing_cells"] > 0


def test_provisional_indicators_marked_in_metadata(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies exit criterion: PROVISIONAL indicators are visibly recorded in Run Metadata."""
    reg_df, kp_df = sample_synthetic_data

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = build_reporting_package(
            cleaned_register=reg_df,
            cleaned_kplhiv=kp_df,
            population="FSW",
            period_mode="SEM",
            output_dir=tmpdir,
            provisional_indicators=["HTS_SEM (OQ-06)", "ViralLoad_Suppression (OQ-09)"],
        )

        wb = openpyxl.load_workbook(pkg["master_workbook"])
        meta_ws = wb["Run Metadata"]
        provisional_cell = None
        for r in range(1, meta_ws.max_row + 1):
            if str(meta_ws.cell(row=r, column=1).value) == "Provisional Indicators":
                provisional_cell = meta_ws.cell(row=r, column=2).value
                break

        assert provisional_cell is not None
        assert "HTS_SEM (OQ-06)" in str(provisional_cell)
        assert "ViralLoad_Suppression (OQ-09)" in str(provisional_cell)


def test_oracle_differential_comparison(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies exit criterion: Exporter output matches oracle calculations under legacy switches, while preserving missing geography."""
    from oracle.runner import run_oracle_from_dfs

    reg_df, kp_df = sample_synthetic_data
    compat = CompatSwitches(
        legacy_capitalize_vocabulary=True,
        legacy_missing_age_below_15=True,
        legacy_impute_missing_sex_f=True,
        legacy_row_sum_flags=True,
        legacy_lexicographic_column_sort=True,
    )

    summary_engine = build_export_summary(
        reg_df, kp_df, population="FSW", period_mode="SEM", compat=compat
    )
    oracle_res = run_oracle_from_dfs(reg_df, kp_df, population="FSW")
    oracle_summary = oracle_res["final_summary"]

    # On complete geography records, engine matches oracle exactly
    complete_geo = summary_engine[
        (summary_engine["county"] != "(MISSING)")
        & (summary_engine["sr_name"] != "(MISSING)")
        & (summary_engine["region"] != "(MISSING)")
    ]

    common_cols = [
        c
        for c in ["TotalCohort", "HTSQ1", "DefinedPackage_Q1", "New_on_ART"]
        if c in complete_geo.columns and c in oracle_summary.columns
    ]
    for col in common_cols:
        assert complete_geo[col].sum() == oracle_summary[col].sum()

    # The engine captures ALL 50 clients (including the 4 with missing geography that legacy notebook dropped)
    assert summary_engine["TotalCohort"].sum() == reg_df["kp_vp_unique_identifier_code"].nunique()


def test_dqa_exceptions_populated_table() -> None:
    """Verifies DQA exceptions exporter with non-empty exception records (Critical and Major)."""
    exc_df = pd.DataFrame(
        [
            {
                "Rule ID": "DQA_DUP_UIC",
                "Severity": "CRITICAL",
                "UIC": "FSW0001",
                "County": "Nairobi",
                "Sub-Recipient": "SR Alpha",
                "Offending Columns": "kp_vp_unique_identifier_code",
                "Suggested Action": "Review duplicate row",
            },
            {
                "Rule ID": "DQA_HIV_POS_NO_ART",
                "Severity": "MAJOR",
                "UIC": "FSW0002",
                "County": "Mombasa",
                "Sub-Recipient": "SR Beta",
                "Offending Columns": "currently_on_art",
                "Suggested Action": "Verify ART linkage",
            },
        ]
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        out_p = Path(tmpdir) / "dqa_populated.xlsx"
        export_dqa_exceptions_workbook(exc_df, output_path=out_p)

        wb = openpyxl.load_workbook(out_p)
        ws = wb["DQA_Exceptions"]
        assert ws.cell(row=2, column=1).value == "DQA_DUP_UIC"
        assert ws.cell(row=3, column=1).value == "DQA_HIV_POS_NO_ART"


def test_cleaned_data_standalone_workbook(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies standalone cleaned data workbook export."""
    reg_df, kp_df = sample_synthetic_data
    with tempfile.TemporaryDirectory() as tmpdir:
        out_p = Path(tmpdir) / "cleaned_data.xlsx"
        export_cleaned_data_workbook(reg_df, kp_df, output_path=out_p, mask_identifiers=True)

        wb = openpyxl.load_workbook(out_p)
        assert "Cleaned Register" in wb.sheetnames
        assert "Cleaned KPLHIV" in wb.sheetnames


def test_template_manager_error_handling() -> None:
    """Verifies error handling in template manager for invalid layout and mismatched blocks."""
    from reporting.template_manager import LayoutBlock, get_template_manager

    mgr = get_template_manager()
    with pytest.raises(KeyError, match="Unknown layout"):
        mgr.get_layout("non_existent_layout")

    with pytest.raises(ValueError, match="mismatched subheaders"):
        LayoutBlock(group="GRP", subheaders=["S1", "S2"], columns=["C1"])


def test_workbook_validator_corruptions(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies that validator detects missing sheets and formula corruption."""
    reg_df, kp_df = sample_synthetic_data
    summary = build_export_summary(reg_df, kp_df, population="FSW", period_mode="SEM")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_p = Path(tmpdir) / "corrupt.xlsx"
        export_summary_workbook(summary, population="FSW", period_mode="SEM", output_path=out_p)

        # Corrupt file by renaming sheet
        wb = openpyxl.load_workbook(out_p)
        wb["Summary"].title = "WrongSheetName"
        wb.save(out_p)

        res = validate_summary_workbook(out_p, population="FSW", period_mode="SEM")
        assert res.is_valid is False
        assert any(i.issue_type == "MissingSheet" for i in res.issues)

        # Corrupt file with row height and wrong total label
        export_summary_workbook(summary, population="FSW", period_mode="SEM", output_path=out_p)
        wb = openpyxl.load_workbook(out_p)
        ws = wb["Summary"]
        ws.row_dimensions[1].height = 50
        ws.row_dimensions[2].height = 50
        ws.cell(row=ws.max_row, column=1, value="WRONG_LABEL")
        wb.save(out_p)

        res2 = validate_summary_workbook(out_p, population="FSW", period_mode="SEM")
        assert res2.is_valid is False
        assert any(i.issue_type == "RowHeight" for i in res2.issues)
        assert any(i.issue_type == "TotalLabel" for i in res2.issues)


def test_reporting_edge_cases_and_coverage(
    sample_synthetic_data: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifies edge cases in summary building, validator, and template fallback."""
    from reporting.excel_exporter import export_summary_sheet
    from reporting.template_manager import get_template_manager, load_template_config

    reg_df, kp_df = sample_synthetic_data
    mgr = get_template_manager()

    # 1. Fallback group color
    assert mgr.get_group_fill("UNKNOWN_NON_EXISTENT_GROUP") == mgr.fills.fallback

    # 2. FileNotFoundError in load_template_config
    with pytest.raises(FileNotFoundError):
        load_template_config("non_existent_file.yaml")

    # 3. FileNotFoundError in validate_summary_workbook
    with pytest.raises(FileNotFoundError):
        validate_summary_workbook("non_existent_wb.xlsx", "FSW", "SEM")

    # 4. Summary builder with aliased UIC column and empty KPLHIV
    aliased_reg = reg_df.rename(columns={"kp_vp_unique_identifier_code": "uic"})
    sum_aliased = build_export_summary(
        aliased_reg, pd.DataFrame(), population="FSW", period_mode="SEM"
    )
    assert not sum_aliased.empty

    # 5. Export into existing sheet name in openpyxl workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Summary"
    layout = mgr.get_layout("semester_standard")
    export_summary_sheet(wb, "Summary", sum_aliased, layout)
    assert "Summary" in wb.sheetnames
