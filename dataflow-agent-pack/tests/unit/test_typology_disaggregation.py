"""Unit tests for Typology-Aware Age/Sex Disaggregation & Period Reporting."""

import openpyxl
import pandas as pd

from analytics.demographics import compute_kpi_demographic_summary
from core.population_rules import (
    get_kpi_indicators_for_period,
    get_typology_column_count,
    get_typology_subheaders,
)
from reporting.excel_exporter import export_age_sex_disaggregation_sheet


def test_typology_rules_configuration():
    """Validates configuration dimensions and labels for each population."""
    # FSW: Female-only, 4 columns per indicator -> 15 columns total
    assert get_typology_subheaders("FSW") == ["15-19_F", "20-24_F", "25+_F", "Total"]
    assert get_typology_column_count("FSW") == 15

    # MSM: Male-only, 4 columns per indicator -> 15 columns total
    assert get_typology_subheaders("MSM") == ["15-19_M", "20-24_M", "25+_M", "Total"]
    assert get_typology_column_count("MSM") == 15

    # PWID, TG, VP: Both sexes, 7 columns per indicator -> 24 columns total
    both_sex_labels = [
        "15-19_M",
        "15-19_F",
        "20-24_M",
        "20-24_F",
        "25+_M",
        "25+_F",
        "Total",
    ]
    for pop in ["PWID", "TG", "VP"]:
        assert get_typology_subheaders(pop) == both_sex_labels
        assert get_typology_column_count(pop) == 24


def test_fsw_kpi_demographic_calculation():
    """Asserts FSW KPI table generates female-only columns and does not coerce unexpected male records."""
    data = {
        "sr_name": ["SR1", "SR1", "SR1", "SR1"],
        "region": ["Coast", "Coast", "Coast", "Coast"],
        "county": ["Mombasa", "Mombasa", "Mombasa", "Mombasa"],
        "age": [17, 22, 28, 22],
        "sex": ["F", "F", "F", "M"],  # 1 unexpected male client
        "definedpackage_q1": [1, 1, 1, 1],
        "hts_q1": [1, 0, 1, 1],
        "prep_q1": [0, 1, 1, 1],
    }
    df = pd.DataFrame(data)

    res = compute_kpi_demographic_summary(df, population="FSW", period_mode="Q1")

    # Demographic columns (3) + 3 indicators * 4 = 15 columns
    assert len(res.columns) == 15
    assert not any("_M" in c for c in res.columns), "FSW KPI must NOT contain male columns"

    row = res.iloc[0]
    # Defined package: 3 females (17->15-19, 22->20-24, 28->25+). Male record excluded from female totals!
    assert row["DEFINED PACKAGE_15-19_F"] == 1
    assert row["DEFINED PACKAGE_20-24_F"] == 1
    assert row["DEFINED PACKAGE_25+_F"] == 1
    assert row["DEFINED PACKAGE_Total"] == 3  # Sum of female columns only

    # HTS: 17(F)=1, 22(F)=0, 28(F)=1. Male excluded.
    assert row["HTS_15-19_F"] == 1
    assert row["HTS_20-24_F"] == 0
    assert row["HTS_25+_F"] == 1
    assert row["HTS_Total"] == 2


def test_msm_kpi_demographic_calculation():
    """Asserts MSM KPI table generates male-only columns and does not coerce unexpected female records."""
    data = {
        "sr_name": ["SR1", "SR1", "SR1", "SR1"],
        "region": ["Nairobi", "Nairobi", "Nairobi", "Nairobi"],
        "county": ["Nairobi", "Nairobi", "Nairobi", "Nairobi"],
        "age": [18, 23, 30, 23],
        "sex": ["M", "M", "M", "F"],  # 1 unexpected female client
        "definedpackage_q1": [1, 1, 1, 1],
        "hts_q1": [1, 1, 0, 1],
        "prep_q1": [1, 0, 1, 1],
    }
    df = pd.DataFrame(data)

    res = compute_kpi_demographic_summary(df, population="MSM", period_mode="Q1")

    assert len(res.columns) == 15
    assert not any("_F" in c for c in res.columns), "MSM KPI must NOT contain female columns"

    row = res.iloc[0]
    assert row["DEFINED PACKAGE_15-19_M"] == 1
    assert row["DEFINED PACKAGE_20-24_M"] == 1
    assert row["DEFINED PACKAGE_25+_M"] == 1
    assert row["DEFINED PACKAGE_Total"] == 3


def test_pwid_tg_vp_kpi_demographic_calculation():
    """Asserts PWID, TG, and VP generate full 24-column summaries."""
    data = {
        "sr_name": ["SR1", "SR1"],
        "region": ["R1", "R1"],
        "county": ["C1", "C1"],
        "age": [18, 23],
        "sex": ["M", "F"],
        "definedpackage_sem": [1, 1],
        "hts_sem_any": [1, 1],
        "prep_sem": [1, 1],
    }
    df = pd.DataFrame(data)

    for pop in ["PWID", "TG", "VP"]:
        res = compute_kpi_demographic_summary(df, population=pop, period_mode="SEM")
        assert len(res.columns) == 24, f"{pop} KPI must contain 24 columns"
        assert any("_M" in c for c in res.columns)
        assert any("_F" in c for c in res.columns)


def test_period_specific_indicators_mapping():
    """Verifies that period modes Q1, Q2, and SEM select the correct indicator columns."""
    q1_map = get_kpi_indicators_for_period("Q1")
    assert "definedpackage_q1" in q1_map
    assert "hts_q1" in q1_map
    assert "prep_q1" in q1_map

    q2_map = get_kpi_indicators_for_period("Q2")
    assert "definedpackage_q2" in q2_map
    assert "hts_q2" in q2_map
    assert "prep_q2" in q2_map

    sem_map = get_kpi_indicators_for_period("SEM")
    assert "definedpackage_sem" in sem_map
    assert "hts_sem_any" in sem_map
    assert "prep_sem" in sem_map


def test_fsw_excel_export_structure():
    """Asserts that Excel export for FSW produces exactly 15 columns with merged headers and SUM formulas."""
    data = {
        "sr_name": ["SR_A", "SR_B"],
        "region": ["R1", "R2"],
        "county": ["C1", "C2"],
        "age": [16, 26],
        "sex": ["F", "F"],
        "definedpackage_q1": [1, 1],
        "hts_q1": [1, 0],
        "prep_q1": [0, 1],
    }
    df = pd.DataFrame(data)

    wb = openpyxl.Workbook()
    ws = export_age_sex_disaggregation_sheet(
        workbook=wb,
        sheet_name="KPI_Disaggregation",
        register_df=df,
        population="FSW",
        period_mode="Q1",
    )

    # Max columns must be exactly 15 (A to O)
    assert ws.max_column == 15

    # Check Row 1 group headers and merged ranges
    # DEFINED PACKAGE: cols 4..7 (D to G)
    # HTS: cols 8..11 (H to K)
    # PREP: cols 12..15 (L to O)
    assert ws.cell(1, 1).value == "DEMOGRAPHICS"
    assert ws.cell(1, 4).value == "DEFINED PACKAGE"
    assert ws.cell(1, 8).value == "HTS"
    assert ws.cell(1, 12).value == "PREP"

    # Check Row 2 subheaders
    assert ws.cell(2, 4).value == "15-19_F"
    assert ws.cell(2, 5).value == "20-24_F"
    assert ws.cell(2, 6).value == "25+_F"
    assert ws.cell(2, 7).value == "Total"

    # Check TOTAL row formulas
    total_r = 3 + len(df)  # Row 5
    assert ws.cell(total_r, 1).value == "TOTAL"
    assert "=SUM(D3:D4)" in str(ws.cell(total_r, 4).value)
    assert "=SUM(O3:O4)" in str(ws.cell(total_r, 15).value)
