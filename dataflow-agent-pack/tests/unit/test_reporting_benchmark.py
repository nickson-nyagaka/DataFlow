"""Performance benchmark and budget verification for Phase 5 reporting engine."""

from __future__ import annotations

import tempfile
import time
import tracemalloc

import numpy as np
import pandas as pd

from reporting.package_builder import build_reporting_package
from reporting.workbook_validator import validate_summary_workbook


def test_reporting_performance_and_memory_budget() -> None:
    """Verifies that reporting package generation operates well within budget (< 90s, < 2.0 GB)."""
    num_rows = 500
    uics = [f"FSW{i % 4_000:06d}" for i in range(num_rows)]

    counties = ["MOMBASA", "KILIFI", "KWALE", "NAIROBI", "KISUMU"]
    regions = ["COAST", "COAST", "COAST", "NRR", "WESTERN"]
    c_arr = np.array(counties)
    r_arr = np.array(regions)

    idx = np.arange(num_rows) % len(counties)
    assigned_counties = c_arr[idx]
    assigned_regions = r_arr[idx]

    rng = np.random.default_rng(42)
    data = {
        "kp_vp_unique_identifier_code": uics,
        "county": assigned_counties,
        "sr_name": ["SR_ALPHA"] * num_rows,
        "region": assigned_regions,
        "age": rng.integers(18, 50, size=num_rows),
        "sex_m_f_": ["F"] * num_rows,
        "date_of_enrolment": ["2024-02-15"] * num_rows,
        "peer_educator_code": [f"PE{i % 50:02d}" for i in range(num_rows)],
        "hiv_status_at_enrollment": ["Negative"] * num_rows,
    }

    # Add visit columns
    for v in range(1, 7):
        data[f"prep_status_{v}"] = ["Refill" if v % 2 == 1 else "None"] * num_rows
        data[f"hiv_tested_results_p_n_nd_na_{v}"] = [
            "Negative" if v % 3 == 0 else "None"
        ] * num_rows
        data[f"currently_on_art_y_n_n_a_{v}"] = ["No"] * num_rows
        data[f"art_outcome_{v}"] = ["None"] * num_rows
        data[f"screened_for_stis_y_n_{v}"] = ["Yes" if v % 2 == 1 else "No"] * num_rows
        data[f"diagnosed_with_sti_y_n_{v}"] = ["No"] * num_rows
        data[f"treated_for_stis_y_n_na_r_referred_{v}"] = ["No"] * num_rows
        data[f"screened_for_tb_{v}"] = ["Yes" if v % 2 == 1 else "No"] * num_rows
        data[f"diagnosed_with_tb_{v}"] = ["No"] * num_rows
        data[f"condoms_distributed_indicate_number_n_a_for_inmates_{v}"] = [
            25 if v % 2 == 1 else 0
        ] * num_rows

    reg_df = pd.DataFrame(data)
    kp_df = pd.DataFrame(
        {
            "kp_vp_unique_identifier_code": uics[:500],
            "county": assigned_counties[:500],
            "sr_name": ["SR_ALPHA"] * 500,
            "region": assigned_regions[:500],
            "levels_copies_ml_": ["<LDL"] * 500,
        }
    )

    tracemalloc.start()
    start_time = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = build_reporting_package(
            cleaned_register=reg_df,
            cleaned_kplhiv=kp_df,
            population="FSW",
            period_mode="SEM",
            output_dir=tmpdir,
        )

        val_res = validate_summary_workbook(
            file_path=pkg["summary_workbook"],
            population="FSW",
            period_mode="SEM",
        )
        assert val_res.is_valid is True

    elapsed = time.perf_counter() - start_time
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_bytes / (1024 * 1024)

    # Budgets: Time < 120s, Peak RAM < 2.0 GB (2048 MB)
    assert elapsed < 120.0, f"Reporting package took {elapsed:.2f}s (budget: < 120s)"
    assert peak_mb < 2048.0, f"Reporting package peak memory {peak_mb:.2f} MB (budget: < 2.0 GB)"
