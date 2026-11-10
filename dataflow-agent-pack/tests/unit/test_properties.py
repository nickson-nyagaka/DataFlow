"""Hypothesis property-based tests for DATAFLOW analytical engine invariants."""

from __future__ import annotations

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from analytics.engine import run_analytics
from core.compat import CompatSwitches


@st.composite
def random_cohort_data(draw):
    """Generates random valid Register DataFrames for property testing."""
    num_rows = draw(st.integers(min_value=5, max_value=40))
    # Allow duplicate UICs to test deduplication
    num_uics = draw(st.integers(min_value=3, max_value=num_rows))
    uic_pool = [f"U{i:03d}" for i in range(num_uics)]

    uics = [draw(st.sampled_from(uic_pool)) for _ in range(num_rows)]
    counties = [draw(st.sampled_from(["MOMBASA", "KILIFI", "NAIROBI"])) for _ in range(num_rows)]
    sr_names = [draw(st.sampled_from(["SR_A", "SR_B"])) for _ in range(num_rows)]
    regions = [draw(st.sampled_from(["COAST", "NRR"])) for _ in range(num_rows)]
    ages = [
        draw(st.one_of(st.none(), st.integers(min_value=12, max_value=65))) for _ in range(num_rows)
    ]
    sexes = [draw(st.sampled_from(["M", "F", None])) for _ in range(num_rows)]

    hts_q1_vals = [draw(st.sampled_from(["Negative", "Positive", "None"])) for _ in range(num_rows)]
    hts_q2_vals = [draw(st.sampled_from(["Negative", "Positive", "None"])) for _ in range(num_rows)]
    prep_q1_vals = [draw(st.sampled_from(["Refill", "Initiated", "None"])) for _ in range(num_rows)]
    prep_q2_vals = [draw(st.sampled_from(["Refill", "None"])) for _ in range(num_rows)]
    condom_vals = [draw(st.integers(min_value=0, max_value=50)) for _ in range(num_rows)]

    data = {
        "kp_vp_unique_identifier_code": uics,
        "county": counties,
        "sr_name": sr_names,
        "region": regions,
        "age": ages,
        "sex_m_f_": sexes,
        "date_of_enrolment": ["2024-03-01"] * num_rows,
        "peer_educator_code": ["PE1"] * num_rows,
        "hiv_tested_results_p_n_nd_na_1": hts_q1_vals,
        "hiv_tested_results_p_n_nd_na_2": ["None"] * num_rows,
        "hiv_tested_results_p_n_nd_na_3": ["None"] * num_rows,
        "hiv_tested_results_p_n_nd_na_4": hts_q2_vals,
        "hiv_tested_results_p_n_nd_na_5": ["None"] * num_rows,
        "hiv_tested_results_p_n_nd_na_6": ["None"] * num_rows,
        "prep_status_1": prep_q1_vals,
        "prep_status_2": ["None"] * num_rows,
        "prep_status_3": ["None"] * num_rows,
        "prep_status_4": prep_q2_vals,
        "prep_status_5": ["None"] * num_rows,
        "prep_status_6": ["None"] * num_rows,
        "screened_for_stis_y_n_1": ["Yes"] * num_rows,
        "screened_for_stis_y_n_2": ["No"] * num_rows,
        "screened_for_stis_y_n_3": ["No"] * num_rows,
        "screened_for_stis_y_n_4": ["No"] * num_rows,
        "screened_for_stis_y_n_5": ["No"] * num_rows,
        "screened_for_stis_y_n_6": ["No"] * num_rows,
        "screened_for_tb_1": ["Yes"] * num_rows,
        "screened_for_tb_2": ["No"] * num_rows,
        "screened_for_tb_3": ["No"] * num_rows,
        "screened_for_tb_4": ["No"] * num_rows,
        "screened_for_tb_5": ["No"] * num_rows,
        "screened_for_tb_6": ["No"] * num_rows,
        "condoms_distributed_indicate_number_n_a_for_inmates_1": condom_vals,
        "condoms_distributed_indicate_number_n_a_for_inmates_2": [0] * num_rows,
        "condoms_distributed_indicate_number_n_a_for_inmates_3": [0] * num_rows,
        "condoms_distributed_indicate_number_n_a_for_inmates_4": [0] * num_rows,
        "condoms_distributed_indicate_number_n_a_for_inmates_5": [0] * num_rows,
        "condoms_distributed_indicate_number_n_a_for_inmates_6": [0] * num_rows,
        "received_peer_education_y_n_1": ["Yes"] * num_rows,
        "received_peer_education_y_n_2": ["No"] * num_rows,
        "received_peer_education_y_n_3": ["No"] * num_rows,
        "received_peer_education_y_n_4": ["No"] * num_rows,
        "received_peer_education_y_n_5": ["No"] * num_rows,
        "received_peer_education_y_n_6": ["No"] * num_rows,
        "provided_with_risk_reduction_counselling_y_n_1": ["No"] * num_rows,
        "provided_with_risk_reduction_counselling_y_n_2": ["No"] * num_rows,
        "provided_with_risk_reduction_counselling_y_n_3": ["No"] * num_rows,
        "provided_with_risk_reduction_counselling_y_n_4": ["No"] * num_rows,
        "provided_with_risk_reduction_counselling_y_n_5": ["No"] * num_rows,
        "provided_with_risk_reduction_counselling_y_n_6": ["No"] * num_rows,
    }
    return pd.DataFrame(data)


@settings(max_examples=25, deadline=None)
@given(df=random_cohort_data())
def test_property_client_grain_le_total_cohort(df: pd.DataFrame):
    """Property 1: In modern mode, any client-grain indicator count <= TotalCohort."""
    res = run_analytics(df, population="FSW", compat=CompatSwitches.all_disabled())
    summary = res["summary_register"]

    for _, row in summary.iterrows():
        total = row["TotalCohort"]
        assert row["HTSQ1"] <= total
        assert row["HTSQ2"] <= total
        assert row["HTS_SEM"] <= total
        assert row["PREP_Q1"] <= total
        assert row["PREP_SEM"] <= total
        assert row["DefinedPackage_Q1"] <= total
        assert row["DefinedPackage_SEM"] <= total


@settings(max_examples=25, deadline=None)
@given(df=random_cohort_data())
def test_property_q1_subset_of_semester(df: pd.DataFrame):
    """Property 2: Any client tested/reached in Q1 is reached in Semester (Q1 subset of SEM)."""
    res = run_analytics(df, population="FSW", compat=CompatSwitches.all_disabled())
    cleaned = res["cleaned_register"]

    # hts_q1 == 1 implies hts_sem == 1
    q1_tested = cleaned[cleaned["hts_q1"] == 1]
    assert (q1_tested["hts_sem"] == 1).all()

    # prep_q1 == 1 implies prep_sem == 1
    q1_prep = cleaned[cleaned["prep_q1"] == 1]
    assert (q1_prep["prep_sem"] == 1).all()


@settings(max_examples=25, deadline=None)
@given(df=random_cohort_data())
def test_property_order_invariance(df: pd.DataFrame):
    """Property 4: Engine outputs are strictly invariant to input row ordering."""
    res1 = (
        run_analytics(df, population="FSW", compat=CompatSwitches.all_disabled())["final_summary"]
        .sort_values(["county", "sr_name", "region"])
        .reset_index(drop=True)
    )

    # Shuffle rows randomly
    shuffled_df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    res2 = (
        run_analytics(shuffled_df, population="FSW", compat=CompatSwitches.all_disabled())[
            "final_summary"
        ]
        .sort_values(["county", "sr_name", "region"])
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(res1, res2)


@settings(max_examples=25, deadline=None)
@given(df=random_cohort_data())
def test_property_age_groups_exhaustive(df: pd.DataFrame):
    """Property 3: Sum of all age groups (including Unknown) equals the total rows in the cohort."""
    res = run_analytics(df, population="FSW", compat=CompatSwitches.all_disabled())
    age_counts = res["age_group_counts"]

    # Sum across age columns for each county x sr_name x region
    age_cols = [
        c for c in ["15-19", "20-24", "25+", "Below 15", "Unknown"] if c in age_counts.columns
    ]
    age_counts["total_ages"] = age_counts[age_cols].sum(axis=1)

    group_sizes = (
        df.groupby(["county", "sr_name", "region"]).size().reset_index(name="expected_total")
    )
    merged = pd.merge(age_counts, group_sizes, on=["county", "sr_name", "region"])
    assert (merged["total_ages"] == merged["expected_total"]).all()
