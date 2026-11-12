"""Integration tests verifying dynamic KP template mapping and NSP handling for PWID.

Ensures DATAFLOW is fully accommodating of all KP typologies (FSW, MSM, TG, PWID, VP)
and handles variable demographic column widths (e.g., 20 columns with extra partner columns)
without treating any single typology as the sole 'source of truth'.
"""

from __future__ import annotations

from pathlib import Path
import openpyxl
import pandas as pd
import pytest

from analytics.engine import run_analytics
from core.config_models import load_population_config
from core.ingestion import ingest_workbook
from core.template_schema import (
    REGISTER_DEMOGRAPHIC_HEADERS,
    REGISTER_ENCOUNTER_HEADERS,
    build_register_template_mapping,
    find_encounter_block_starts,
    is_kp_template_register,
)
from reporting.package_builder import build_export_summary


def test_pwid_with_20_demographic_columns_detected_and_mapped(tmp_path: Path):
    """Verifies that an extra demographic column (e.g. Unnamed: 4) shifts encounter starts to [20, 73, ...]
    and is dynamically detected and mapped without error.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Register"
    ws.append(["Title"])
    ws.append([])

    demo_headers = list(REGISTER_DEMOGRAPHIC_HEADERS[:4]) + ["Partner_Extra"] + list(REGISTER_DEMOGRAPHIC_HEADERS[4:])
    headers = list(demo_headers)
    for enc in range(6):
        headers.extend(REGISTER_ENCOUNTER_HEADERS)
    ws.append(headers)

    row = ["Coast", "MEWA", "Kilifi", "Kilifi South", "P01", "Ward 1", "Spot A", "John Doe", "0700000000", "PWID_001", "PWID", "01/01/1995", 29, "M", "01/01/2023", "01/01/2024", "Negative", "", "PE01", "PE01"]
    for enc in range(6):
        v = ["No"] * 53
        v[0] = "Yes"
        v[20] = 50
        row.extend(v)
    ws.append(row)

    ws_kp = wb.create_sheet("KPLHIV")
    ws_kp.append(["Title"])
    ws_kp.append([])
    ws_kp.append(["UIC", "County"])

    test_file = tmp_path / "test_pwid_20cols.xlsx"
    wb.save(test_file)

    reg_df, kp_df, _ = ingest_workbook(test_file, load_population_config("PWID"))

    assert len(reg_df.columns) == 338
    assert reg_df.columns[20] == "received_peer_education_y_n_1"
    assert reg_df.columns[40] == "needles_and_syringes_distributed_indicate_number_n_a_for_inmates_1"
    assert reg_df.columns[73] == "received_peer_education_y_n_2"
    assert reg_df.columns[93] == "needles_and_syringes_distributed_indicate_number_n_a_for_inmates_2"
    assert reg_df.columns[285] == "received_peer_education_y_n_6"


def test_pwid_nsp_indicator_calculation_and_summary(tmp_path: Path):
    """Verifies that when needles and syringes are distributed, PWID accurately calculates
    NSP reach and volume indicators in both Q1 and Semester.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Register"
    ws.append(["Title"])
    ws.append([])

    demo_headers = list(REGISTER_DEMOGRAPHIC_HEADERS[:4]) + ["Partner_Extra"] + list(REGISTER_DEMOGRAPHIC_HEADERS[4:])
    headers = list(demo_headers)
    for enc in range(6):
        headers.extend(REGISTER_ENCOUNTER_HEADERS)
    ws.append(headers)

    row = ["Coast", "MEWA", "Kilifi", "Kilifi South", "P01", "Ward 1", "Spot A", "John Doe", "0700000000", "PWID_001", "PWID", "01/01/1995", 29, "M", "01/01/2023", "01/01/2024", "Negative", "", "PE01", "PE01"]
    for enc in range(6):
        v = ["No"] * 53
        if enc == 0:
            v[0] = "Yes"
            v[1] = "Facility"
            v[2] = "Negative"
            v[16] = 20
            v[20] = 50
        elif enc == 3:
            v[20] = 75
        row.extend(v)
    ws.append(row)

    ws_kp = wb.create_sheet("KPLHIV")
    ws_kp.append(["Title"])
    ws_kp.append([])
    ws_kp.append(["UIC", "County"])

    test_file = tmp_path / "test_pwid_nsp.xlsx"
    wb.save(test_file)

    reg_df, kp_df, _ = ingest_workbook(test_file, load_population_config("PWID"))

    analytics = run_analytics(reg_df, kp_df, population="PWID")
    clean_reg = analytics["cleaned_register"]

    assert clean_reg.loc[0, "nsp_q1"] == 1
    assert clean_reg.loc[0, "nsp_q2"] == 1
    assert clean_reg.loc[0, "nsp_sem"] == 1
    assert clean_reg.loc[0, "total_nsp_q1"] == 50
    assert clean_reg.loc[0, "total_nsp_q2"] == 75
    assert clean_reg.loc[0, "total_nsp_sem"] == 125

    export_df = build_export_summary(clean_reg, kp_df, population="PWID", period_mode="SEM")
    assert len(export_df) == 1
    row_sum = export_df.iloc[0]

    assert row_sum["NSP_Q1"] == 1
    assert row_sum["NSP_Q2"] == 1
    assert row_sum["NSP_SEM"] == 1
    assert row_sum["total_nsp_Q1"] == 50
    assert row_sum["total_nsp_Q2"] == 75
    assert row_sum["total_nsp_SEM"] == 125
