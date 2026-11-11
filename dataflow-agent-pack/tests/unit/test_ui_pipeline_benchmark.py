"""Phase 6 End-to-End Pipeline Performance Benchmark.

Verifies Phase 6 Exit Criterion:
"Upload -> Process -> Download completes on synthetic cohort (time and memory reported)."
"""

from __future__ import annotations

import io
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

from core.runner import compute_file_hash, run_full_pipeline
from ui.upload import validate_uploaded_bytes


def test_ui_full_pipeline_benchmark(tmp_path: Path):
    """
    Simulates Upload -> Process -> Download end-to-end pipeline execution,
    measuring and reporting wall-clock time and peak memory.
    """
    num_rows = 1_000
    uics = [f"FSW{i % 800:06d}" for i in range(num_rows)]

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

    # Add 10 visit encounter columns
    for v in range(1, 11):
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

    # Save to Excel bytes (simulating user file upload)
    upload_buf = io.BytesIO()
    with pd.ExcelWriter(upload_buf, engine="openpyxl") as writer:
        reg_df.to_excel(writer, sheet_name="Register", index=False)
        kp_df.to_excel(writer, sheet_name="KPLHIV", index=False)
    file_bytes = upload_buf.getvalue()

    tracemalloc.start()
    t_start = time.perf_counter()

    # Step 1: Upload validation & hashing
    file_hash = compute_file_hash(file_bytes)
    assert len(file_hash) == 64
    is_valid, err = validate_uploaded_bytes(file_bytes, "cohort_10k.xlsx", "FSW")
    assert is_valid is True
    assert err is None

    # Step 2: Full pipeline execution (Ingestion -> Cleaning -> DQA -> Analytics -> Packages)
    result = run_full_pipeline(
        file_source=file_bytes,
        file_name="cohort_10k.xlsx",
        population="FSW",
        period_mode="SEM",
        force_rerun=True,
    )

    # Step 3: Verification of generated packages
    master_path = result.package_paths["master_workbook"]
    zip_path = result.package_paths["zip_package"]
    assert master_path.exists()
    assert zip_path.exists()

    # Step 4: Download simulation (reading bytes from disk)
    master_download_bytes = master_path.read_bytes()
    zip_download_bytes = zip_path.read_bytes()
    assert len(master_download_bytes) > 0
    assert len(zip_download_bytes) > 0

    elapsed = time.perf_counter() - t_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_bytes / (1024 * 1024)

    print("\n=======================================================")
    print("PHASE 6 E2E PIPELINE BENCHMARK (Upload -> Process -> Download)")
    print("=======================================================")
    print(f"Cohort Size         : {num_rows:,} rows x {len(reg_df.columns)} columns")
    print(f"Total Execution Time: {elapsed:.2f}s (Budget: < 90.0s)")
    print(f"Peak Memory Usage   : {peak_mb:.1f} MB (Budget: < 2,048.0 MB)")
    print(f"Stage Timings       : {result.stage_timings}")
    print(f"Master Package Size : {len(master_download_bytes):,} bytes")
    print(f"Modular ZIP Size    : {len(zip_download_bytes):,} bytes")
    print("=======================================================\n")

    assert elapsed < 90.0, f"Pipeline exceeded 90s time budget: {elapsed:.2f}s"
    assert peak_mb < 2048.0, f"Pipeline exceeded 2.0 GB memory budget: {peak_mb:.1f} MB"
