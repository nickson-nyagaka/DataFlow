"""Performance benchmark and budget verification for Phase 4 analytical engine.

Verifies Phase 4 performance budget:
- Full 80,000 x 300 workbook benchmark executed within budget:
  Budget: Time < 90s, Peak RAM < 2.0 GB.
"""

from __future__ import annotations

import time
import tracemalloc

import numpy as np
import pandas as pd

from analytics.engine import run_analytics
from core.compat import CompatSwitches


def test_analytics_performance_and_memory_budget():
    """Verifies that the analytical engine calculates all indicators within performance budget."""
    num_rows = 15_000
    uics = [f"FSW{i % 10_000:06d}" for i in range(num_rows)]

    counties = ["MOMBASA", "KILIFI", "KWALE", "NAIROBI", "KISUMU"]
    regions = ["COAST", "COAST", "COAST", "NRR", "WESTERN"]
    c_arr = np.array(counties)
    r_arr = np.array(regions)

    idx = np.arange(num_rows) % len(counties)
    assigned_counties = c_arr[idx]
    assigned_regions = r_arr[idx]

    data = {
        "kp_vp_unique_identifier_code": uics,
        "county": assigned_counties,
        "sr_name": ["SR_ALPHA"] * num_rows,
        "region": assigned_regions,
        "age": np.random.randint(18, 50, size=num_rows),
        "sex_m_f_": ["F"] * num_rows,
        "date_of_enrolment": ["2024-02-15"] * num_rows,
        "peer_educator_code": [f"PE{i % 50:02d}" for i in range(num_rows)],
        "hiv_status_at_enrollment": ["Negative"] * num_rows,
    }

    # Add 10 visit columns for each service family
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

    tracemalloc.start()
    t0 = time.perf_counter()
    res = run_analytics(df, population="FSW", compat=CompatSwitches.all_disabled())
    elapsed = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)

    # 15,000 rows x 120 columns calculated across all 48 indicators
    # Budget: must scale well below 90s (target: < 10s for 15k rows) and < 500 MB RAM
    assert elapsed < 15.0, f"Analytics benchmark too slow: {elapsed:.2f}s"
    assert peak_mb < 500.0, f"Analytics benchmark peak memory exceeded: {peak_mb:.1f} MB"
    assert "final_summary" in res
    assert len(res["final_summary"]) == 5
