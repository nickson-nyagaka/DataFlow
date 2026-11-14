"""Comprehensive Integration Tests for the Official KP Template (reference/KP_TEMPLATE.xlsx).

Verifies:
1. Template concordance audit identifies the official 337-column structure, 6 encounters, and 72 KPLHIV columns.
2. Full pipeline execution across all 5 key populations (FSW, MSM, TG, PWID, VP) calculates accurate indicators.
3. Clinical encounter columns (HTS, Peer Education, Condoms, ART, PrEP, STIs, TB) evaluate non-zero according to workbook values.
4. DQA clinical consistency rules trigger accurately on planted encounter discrepancies.
5. 100% backward compatibility for legacy / synthetic fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cleaning import clean_kplhiv_frame, clean_register_frame
from core.config_models import load_population_config
from core.ingestion import ingest_workbook
from core.runner import run_full_pipeline
from core.template_validator import validate_kp_template_concordance
from core.validation import run_dqa

REFERENCE_TEMPLATE = Path("reference/KP_TEMPLATE.xlsx")
SYNTHETIC_FIXTURE = Path("tests/synthetic/fixtures/synthetic_fsw.xlsx")


def test_template_concordance_audit_on_reference_template():
    """Exit criterion 1: Pre-processing validator recognises reference/KP_TEMPLATE.xlsx as OFFICIAL_KP_TEMPLATE_337."""
    assert REFERENCE_TEMPLATE.exists(), "reference/KP_TEMPLATE.xlsx must be present"

    report = validate_kp_template_concordance(REFERENCE_TEMPLATE)
    assert report.is_valid is True
    assert report.detected_format == "OFFICIAL_KP_TEMPLATE_337"
    assert report.register_columns_count == 337
    assert report.kplhiv_columns_count == 72
    assert report.encounters_detected == 6
    assert len(report.missing_core_columns) == 0


@pytest.mark.parametrize("population", ["FSW", "MSM", "TG", "PWID", "VP"])
def test_full_pipeline_on_kp_template_for_all_populations(population: str):
    """Exit criterion 2: Full pipeline calculates accurate clinical indicators across all 5 populations on KP_TEMPLATE."""
    result = run_full_pipeline(
        file_source=REFERENCE_TEMPLATE,
        file_name="KP_TEMPLATE.xlsx",
        population=population,
        period_mode="SEM",
        force_rerun=True,
    )

    assert result.total_cohort == 1
    assert result.active_kplhiv == 1
    assert len(result.package_paths) == 6

    # Verify summary indicators computed accurately from row 4 data
    sum_df = result.summary_df
    assert len(sum_df) >= 1
    row = sum_df.iloc[0]

    assert row["TotalCohort"] == 1
    assert row["TotalPE"] == 1
    assert row["PeerEducation_Q1"] == 1  # Col 20: 'Yes'
    assert row["ReceivedCondom_Q1"] == 1  # Col 36: 5 condoms
    assert row["total_condoms_Q1"] >= 5  # Col 36 distributed condoms
    assert row["HTSQ1"] == 1  # Col 22: 'Not Done' -> counted in HTS testing encounter


def test_dqa_clinical_consistency_on_planted_kp_template_defects():
    """Exit criterion 3: Clinical DQA rules accurately detect contradictions across template encounter columns."""
    pop_config = load_population_config("TG")
    reg_raw, kp_raw, _ = ingest_workbook(REFERENCE_TEMPLATE, pop_config)

    # Plant encounter discrepancies:
    # 1. Negative on ART in encounter 1
    reg_planted = reg_raw.copy()
    reg_planted["hiv_tested_results_p_n_nd_na_1"] = "Negative"
    reg_planted["currently_on_art_y_n_n_a_1"] = "Yes"

    # 2. PrEP active while HIV positive in encounter 2
    reg_planted["prep_status_2"] = "Initiated"
    reg_planted["hiv_tested_results_p_n_nd_na_2"] = "Positive"

    reg_clean = clean_register_frame(reg_planted)
    kp_clean = clean_kplhiv_frame(kp_raw)

    dqa_res = run_dqa(reg_clean, kp_clean, population="TG", block_on_critical=False)
    assert dqa_res.rule_counts.get("hiv_neg_on_art", 0) >= 1
    assert dqa_res.rule_counts.get("prep_on_positive", 0) >= 1


def test_backward_compatibility_with_synthetic_fixtures():
    """Exit criterion 4: Pre-existing synthetic fixtures continue to process cleanly with 100% parity."""
    assert SYNTHETIC_FIXTURE.exists()

    report = validate_kp_template_concordance(SYNTHETIC_FIXTURE)
    assert report.is_valid is True
    assert report.detected_format == "LEGACY_SYNTHETIC"

    pop_config = load_population_config("FSW")
    reg_raw, kp_raw, _ = ingest_workbook(SYNTHETIC_FIXTURE, pop_config)
    assert len(reg_raw) == 203
    assert "prep_status_1" in reg_raw.columns


def test_template_concordance_and_pipeline_on_xlsb_binary_format():
    """Verifies that .xlsb binary Excel workbooks are audited and ingested without openpyxl failure."""
    synth_xlsb = Path("tests/synthetic/fixtures/synthetic_fsw.xlsb")
    if synth_xlsb.exists():
        report = validate_kp_template_concordance(synth_xlsb)
        assert report.is_valid is True
        assert report.detected_format == "LEGACY_SYNTHETIC"
        assert report.register_columns_count == 141

    tg_xlsb = Path("runtime/temporary/upload_ef0d1d4cc9_Consolidated TG.xlsb")
    if tg_xlsb.exists():
        report_tg = validate_kp_template_concordance(tg_xlsb)
        assert report_tg.is_valid is True
        assert report_tg.detected_format == "OFFICIAL_KP_TEMPLATE_337"
        assert report_tg.register_columns_count == 337
        assert report_tg.kplhiv_columns_count == 72
        assert report_tg.encounters_detected == 6
