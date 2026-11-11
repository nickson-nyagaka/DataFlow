"""Full 80,000-row analytical pipeline benchmark for DATAFLOW Phase 4."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
import tracemalloc

import numpy as np
import pandas as pd

from analytics.engine import run_analytics
from core.compat import CompatSwitches


def main():
    num_rows = 80_000
    uics = [f"FSW{i % 40_000:06d}" for i in range(num_rows)]
    counties = ["MOMBASA", "KILIFI", "KWALE", "NAIROBI", "KISUMU"]
    regions = ["COAST", "COAST", "COAST", "NRR", "WESTERN"]
    c_arr, r_arr = np.array(counties), np.array(regions)
    idx = np.arange(num_rows) % len(counties)

    data = {
        "kp_vp_unique_identifier_code": uics,
        "county": c_arr[idx],
        "sr_name": ["SR_ALPHA"] * num_rows,
        "region": r_arr[idx],
        "age": np.random.randint(18, 50, size=num_rows),
        "sex_m_f_": ["F"] * num_rows,
        "date_of_enrolment": ["2024-02-15"] * num_rows,
        "peer_educator_code": [f"PE{i % 100:02d}" for i in range(num_rows)],
        "hiv_status_at_enrollment": ["Negative"] * num_rows,
    }

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
        data[f"received_peer_education_y_n_{v}"] = ["Yes" if v % 2 == 1 else "No"] * num_rows
        data[f"provided_with_risk_reduction_counselling_y_n_{v}"] = [
            "Yes" if v % 2 == 1 else "No"
        ] * num_rows

    df = pd.DataFrame(data)
    print(f"DataFrame shape: {df.shape}")

    tracemalloc.start()
    t0 = time.perf_counter()
    res = run_analytics(df, population="FSW", compat=CompatSwitches.all_disabled())
    elapsed = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(f"Full 80,000 rows analytical pipeline finished in: {elapsed:.2f}s")
    print(f"Peak RAM: {peak_mb:.1f} MB")
    print(f"Summary output rows: {len(res['final_summary'])}")


if __name__ == "__main__":
    main()
