"""Unit test suite for Phase 2: Ingestion, cleaning, audit trail, and inspect CLI.

Covers all Phase 2 exit criteria defined in docs/PHASE_PLAN.md:
1. Multi-format equivalence: XLSX, XLS, and XLSB yield identical frames.
2. Leading zeros and long numeric IDs strictly preserved.
3. Ambiguous alias raises named error listing candidate columns (zero cell data).
4. Renamed column resolved via alias; missing required column produces structured error.
5. Audit trail reconciles: rows_in == rows_out + dropped.
6. Input frame unchanged by cleaning (hash before and after).
7. Case variants of 'Known Positive' recognized; unknown values preserved uncoerced (D-008).
8. Structure-only inspect outputs zero planted cell values.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from core.audit import SheetAudit, WorkbookAudit
from core.cleaning import (
    clean_numeric_id_series,
    clean_register_frame,
    normalize_vocabulary_series,
)
from core.config_models import load_population_config
from core.exceptions import IngestionError
from core.ingestion import (
    ingest_workbook,
    resolve_column_aliases,
)
from core.inspect import format_inspection_report, inspect_workbook

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "synthetic" / "fixtures"


def test_multi_format_equivalence():
    """Exit criterion 1: The same synthetic content as XLSX, XLS and XLSB yields identical frames."""
    cfg = load_population_config("FSW")

    xlsx_path = FIXTURES_DIR / "synthetic_fsw.xlsx"
    xlsb_path = FIXTURES_DIR / "synthetic_fsw.xlsb"
    xls_path = FIXTURES_DIR / "synthetic_fsw.xls"

    assert xlsx_path.exists(), "synthetic_fsw.xlsx missing"
    assert xlsb_path.exists(), "synthetic_fsw.xlsb missing"
    assert xls_path.exists(), "synthetic_fsw.xls missing"

    reg_xlsx, kp_xlsx, audit_xlsx = ingest_workbook(xlsx_path, cfg)
    reg_xlsb, kp_xlsb, audit_xlsb = ingest_workbook(xlsb_path, cfg)
    reg_xls, kp_xls, audit_xls = ingest_workbook(xls_path, cfg)

    # 1. Row and column counts match exactly
    assert reg_xlsx.shape == reg_xlsb.shape == reg_xls.shape
    assert kp_xlsx.shape == kp_xlsb.shape == kp_xls.shape

    # 2. Column names and order match exactly
    assert list(reg_xlsx.columns) == list(reg_xlsb.columns) == list(reg_xls.columns)
    assert list(kp_xlsx.columns) == list(kp_xlsb.columns) == list(kp_xls.columns)

    # 3. Leading UICs and core identifiers match exactly
    pd.testing.assert_series_equal(
        reg_xlsx["kp_vp_unique_identifier_code"],
        reg_xlsb["kp_vp_unique_identifier_code"],
        check_dtype=False,
    )
    pd.testing.assert_series_equal(
        reg_xlsx["kp_vp_unique_identifier_code"],
        reg_xls["kp_vp_unique_identifier_code"],
        check_dtype=False,
    )


def test_leading_zeros_and_long_numeric_ids_preserved():
    """Exit criterion 2: Leading zeros and long numeric IDs preserved without truncation."""
    # Test series with leading zeros in UIC, 10-digit CCC numbers, and PE codes
    raw_uics = pd.Series(["00123", "0000456", "0123456789", "FSW001"])
    cleaned_uics = clean_numeric_id_series(raw_uics)
    assert cleaned_uics.tolist() == ["00123", "0000456", "0123456789", "FSW001"]

    # Test erroneous float suffixes (.0) removed while leading zeros preserved
    raw_cccs = pd.Series(["0123456789.0", "0098765432.00", "2024100001.0"])
    cleaned_cccs = clean_numeric_id_series(raw_cccs)
    assert cleaned_cccs.tolist() == ["0123456789", "0098765432", "2024100001"]


def test_ambiguous_alias_raises_named_error_without_data():
    """Exit criterion 3: Ambiguous alias raises a named error listing candidate columns; no data in the message."""
    alias_map = {
        "kp_vp_unique_identifier_code": ["client_id", "uic_code"],
        "peer_educator_code": ["pe_id"],
    }

    # Case A: Two raw columns map to the same canonical target
    raw_columns = ["client_id", "uic_code", "pe_id"]
    with pytest.raises(IngestionError) as exc_info:
        resolve_column_aliases(raw_columns, alias_map)

    err_msg = str(exc_info.value)
    assert "Ambiguous duplicate column mapping" in err_msg
    assert "kp_vp_unique_identifier_code" in err_msg
    assert "client_id" in err_msg and "uic_code" in err_msg

    # Case B: Ambiguous alias matching multiple targets
    ambiguous_alias_map = {
        "hiv_status": ["status"],
        "prep_status": ["status"],
    }
    with pytest.raises(IngestionError) as exc_b:
        resolve_column_aliases(["status"], ambiguous_alias_map)

    err_b = str(exc_b.value)
    assert "Ambiguous column alias" in err_b
    assert "status" in err_b
    assert "hiv_status" in err_b and "prep_status" in err_b

    # Verify no record-level data values leaked in exception messages
    for msg in [err_msg, err_b]:
        assert "FSW" not in msg
        assert "2024" not in msg
        assert "0712" not in msg


def test_peer_educator_column_disambiguation():
    """Verifies that real registers containing both 'Peer Educator' and 'Peer Educator Code' disambiguate cleanly."""
    alias_map = {
        "kp_vp_unique_identifier_code": ["uic"],
        "peer_educator_code": ["peer_educator_code", "pe_code", "peer_educator"],
        "county": ["county"],
        "date_of_enrolment": ["date_of_enrolment"],
    }

    # Case 1: Both Peer Educator (name) and Peer Educator Code (code) present
    raw_cols_both = ["uic", "Peer Educator", "Peer Educator Code", "county", "date_of_enrolment"]
    mapping_both = resolve_column_aliases(raw_cols_both, alias_map)
    assert mapping_both["Peer Educator Code"] == "peer_educator_code"
    assert "Peer Educator" not in mapping_both

    # Case 2: Only Peer Educator present (fallback mapping)
    raw_cols_pe_only = ["uic", "Peer Educator", "county", "date_of_enrolment"]
    mapping_pe = resolve_column_aliases(raw_cols_pe_only, alias_map)
    assert mapping_pe["Peer Educator"] == "peer_educator_code"

    # Case 3: Both PE Code and Peer Educator present
    raw_cols_pe_code = ["uic", "PE Code", "Peer Educator", "county", "date_of_enrolment"]
    mapping_code = resolve_column_aliases(raw_cols_pe_code, alias_map)
    assert mapping_code["PE Code"] == "peer_educator_code"
    assert "Peer Educator" not in mapping_code


def test_renamed_column_resolved_and_missing_required_column_structured_error():
    """Exit criterion 4: Renamed column resolved via alias; missing required column produces a structured error."""
    alias_map = {
        "kp_vp_unique_identifier_code": ["unique_identifier_code", "program_uic"],
        "county": ["county_name", "county"],
        "date_of_enrolment": ["enrolment_date"],
    }

    # Successful resolution of renamed columns
    raw_cols = ["unique_identifier_code", "county_name", "enrolment_date"]
    mapping = resolve_column_aliases(
        raw_cols, alias_map, required_columns=["kp_vp_unique_identifier_code", "county"]
    )
    assert mapping["unique_identifier_code"] == "kp_vp_unique_identifier_code"
    assert mapping["county_name"] == "county"

    # Missing required column produces structured error
    raw_missing = ["unique_identifier_code"]  # missing 'county'
    with pytest.raises(IngestionError) as exc_info:
        resolve_column_aliases(
            raw_missing, alias_map, required_columns=["kp_vp_unique_identifier_code", "county"]
        )

    err_msg = str(exc_info.value)
    assert "Missing required columns in sheet: ['county']" in err_msg


def test_audit_trail_reconciles_rows_in_out_dropped():
    """Exit criterion 5: Audit trail reconciles: rows in = rows out + rows explicitly dropped."""
    sheet_audit = SheetAudit(
        sheet_name="Register",
        rows_in=100,
        rows_out=90,
        dropped_empty_rows=10,
        dropped_records={},
    )
    assert sheet_audit.reconcile() is True

    # Tampered audit must fail loudly
    bad_audit = SheetAudit(
        sheet_name="Register",
        rows_in=100,
        rows_out=85,  # 85 + 10 != 100
        dropped_empty_rows=10,
    )
    with pytest.raises(IngestionError) as exc_info:
        bad_audit.reconcile()
    assert "Audit trail reconciliation failed" in str(exc_info.value)


def test_input_frame_unchanged_by_cleaning():
    """Exit criterion 6: Input frame unchanged by cleaning (hash before/after)."""
    raw_df = pd.DataFrame(
        {
            "kp_vp_unique_identifier_code": ["  FSW001  ", "FSW002.0", "00345"],
            "sr_name": ["Partner A", None, "Partner B"],
            "age": ["25", " 30 ", "invalid"],
            "date_of_enrolment": ["15/05/2024", "2024-06-01", "45123"],
            "hiv_status_at_enrollment": ["known positive", "Negative", "Unknown_Val"],
        }
    )

    # Record hash of input before cleaning
    hash_before = WorkbookAudit.compute_frame_hash(raw_df)

    # Execute cleaning pipeline
    cleaned_df = clean_register_frame(raw_df)

    # Record hash of input after cleaning
    hash_after = WorkbookAudit.compute_frame_hash(raw_df)

    # Input frame must remain 100% byte-for-byte immutable
    assert hash_before == hash_after
    assert cleaned_df is not raw_df

    # Verify transformations on cleaned copy
    assert cleaned_df["kp_vp_unique_identifier_code"].tolist() == ["FSW001", "FSW002", "00345"]
    assert cleaned_df["sr_name"].tolist() == ["Partner A", "Unknown", "Partner B"]  # D-009
    assert pd.isna(cleaned_df["age"].iloc[2])  # invalid age is NaN, not defaulted
    assert cleaned_df["date_of_enrolment"].iloc[0] == "2024-05-15"


def test_case_variants_of_known_positive_recognized_and_unknowns_not_coerced():
    """Exit criterion 7: Every case variant of 'Known Positive' is recognised; unknown values are reported, not coerced."""
    variants_map = {
        "negative": "Negative",
        "positive": "Positive",
        "known positive": "Known positive",
        "Known Positive": "Known positive",
        "KNOWN POSITIVE": "Known positive",
    }

    raw_series = pd.Series(
        [
            "known positive",
            "Known Positive",
            "KNOWN POSITIVE",
            "negative",
            "Positve_Typo_Not_Coerced",
            "  positive  ",
        ]
    )

    normalized = normalize_vocabulary_series(raw_series, variants_map)

    # 1. Known variants mapped to canonical 'Known positive' / 'Positive' / 'Negative'
    assert normalized.iloc[0] == "Known positive"
    assert normalized.iloc[1] == "Known positive"
    assert normalized.iloc[2] == "Known positive"
    assert normalized.iloc[3] == "Negative"
    assert normalized.iloc[5] == "Positive"

    # 2. Unrecognised value preserved untouched (not coerced, not NaN) per D-008
    assert normalized.iloc[4] == "Positve_Typo_Not_Coerced"


def test_inspect_prints_no_cell_values():
    """Exit criterion 9: inspect prints no cell values (test asserts output contains no planted values)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_wb = Path(tmp_dir) / "secret_workbook.xlsx"

        # Plant distinct canary values that must NEVER appear in output
        canary_uic = "PLANTED_SECRET_UIC_9999"
        canary_ccc = "PLANTED_SECRET_CCC_8888888888"
        canary_name = "SECRET_CLIENT_NAME_JANE"

        df_reg = pd.DataFrame(
            {
                "kp_vp_unique_identifier_code": [canary_uic],
                "ccc_number_nupi_n_a_10_digit_number_": [canary_ccc],
                "client_name": [canary_name],
                "county": ["MOMBASA"],
                "date_of_enrolment": ["2024-01-15"],
            }
        )
        df_kp = pd.DataFrame(
            {
                "kp_vp_unique_identifier_code": [canary_uic],
                "county": ["MOMBASA"],
            }
        )

        with pd.ExcelWriter(tmp_wb, engine="openpyxl") as writer:
            df_reg.to_excel(writer, sheet_name="Register", index=False)
            df_kp.to_excel(writer, sheet_name="KPLHIV", index=False)

        report = inspect_workbook(tmp_wb, population="FSW")
        formatted_output = format_inspection_report(report)

        # Assert zero planted canary values exist in formatted text
        assert canary_uic not in formatted_output
        assert canary_ccc not in formatted_output
        assert canary_name not in formatted_output
        assert "MOMBASA" not in formatted_output

        # Assert structural metadata is correctly printed
        assert "DATAFLOW WORKBOOK STRUCTURE REPORT" in formatted_output
        assert "Register" in formatted_output
        assert "KPLHIV" in formatted_output
        assert "CONFIRMATION: Zero cell values or client identifiers printed" in formatted_output
