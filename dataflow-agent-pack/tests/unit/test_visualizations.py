"""Unit tests for analytics/visualizations/ and extended display analytics contract."""

from __future__ import annotations

import pandas as pd
import pytest

from analytics.display_summary import compute_display_analytics
from analytics.visualizations.charts import (
    create_bullet_chart,
    create_cascade_funnel,
    create_grouped_bar,
    create_lollipop_chart,
    create_population_pyramid,
    create_regional_heatmap,
    create_treemap,
)
from analytics.visualizations.theme import (
    HEIGHT_BULLET,
    HEIGHT_FUNNEL,
    HEIGHT_HEATMAP,
    HEIGHT_LOLLIPOP,
    HEIGHT_PYRAMID,
    HEIGHT_TREEMAP,
)


@pytest.fixture
def mock_display_inputs() -> dict:
    summary_df = pd.DataFrame(
        [
            {
                "county": "MOMBASA",
                "sr_name": "SR ALPHA",
                "region": "COAST",
                "TotalCohort": 100,
                "DefinedPackage_SEM": 85,
                "HTS_SEM": 92,
                "HTS_Positive": 4,
                "HTS_Negative": 88,
                "New_on_ART": 4,
                "PREP_SEM": 30,
                "Total_KPLHIV": 20,
                "Suppressed": 19,
                "total_condoms_SEM": 500,
                "ReceivedCondom_SEM": 80,
                "PeerEducation_SEM": 90,
                "total_nsp_SEM": 0,
            },
            {
                "county": "NAIROBI",
                "sr_name": "SR BETA",
                "region": "NRR",
                "TotalCohort": 200,
                "DefinedPackage_SEM": 150,
                "HTS_SEM": 170,
                "HTS_Positive": 10,
                "HTS_Negative": 160,
                "New_on_ART": 8,
                "PREP_SEM": 60,
                "Total_KPLHIV": 40,
                "Suppressed": 35,
                "total_condoms_SEM": 1000,
                "ReceivedCondom_SEM": 160,
                "PeerEducation_SEM": 180,
                "total_nsp_SEM": 0,
            },
        ]
    )
    reg_analyzed = pd.DataFrame(
        {
            "age_group": ["20-24", "25+", "15-19", "Below 15"],
            "sex_m_f_": ["F", "M", "F", "M"],
        }
    )
    kp_analyzed = pd.DataFrame(
        {
            "standardized_viral_load": [50, 1500, 20, 0],
            "is_suppressed": [1, 0, 1, 1],
        }
    )
    return {
        "summary_df": summary_df,
        "reg_analyzed": reg_analyzed,
        "kp_analyzed": kp_analyzed,
    }


def test_theme_application():
    """Verifies that apply_chart_theme enforces fixed height and clean styling."""
    fig = create_bullet_chart(
        title="Testing Coverage",
        actual=85.0,
        target=90.0,
        numerator=85,
        denominator=100,
    )
    assert fig.layout.height == HEIGHT_BULLET
    assert fig.layout.autosize is True
    assert fig.layout.hoverlabel.bordercolor == "#2C3E50"


def test_cascade_funnel_generation():
    """Verifies funnel chart dimensions and stages."""
    fig = create_cascade_funnel(
        stages=["Tested", "Positive", "Linked"],
        values=[100, 10, 9],
        title="HTS Cascade",
    )
    assert fig.layout.height == HEIGHT_FUNNEL
    assert len(fig.data) == 1
    assert list(fig.data[0].y) == ["Tested", "Positive", "Linked"]


def test_regional_heatmap_generation():
    """Verifies heatmap matrix and height."""
    fig = create_regional_heatmap(
        x_labels=["HTS", "PrEP"],
        y_labels=["COAST", "NRR"],
        z_data=[[90.0, 30.0], [85.0, 25.0]],
        title="Regional Matrix",
    )
    assert fig.layout.height == HEIGHT_HEATMAP
    assert len(fig.data) == 1
    assert fig.data[0].z[0][0] == 90.0


def test_lollipop_chart_generation():
    """Verifies horizontal lollipop rankings."""
    fig = create_lollipop_chart(
        categories=["SR Alpha", "SR Beta"],
        values=[85.0, 92.0],
        title="SR Ranking",
        benchmark_line=90.0,
    )
    assert fig.layout.height == HEIGHT_LOLLIPOP
    assert len(fig.data) == 3  # 2 stem lines + 1 marker trace


def test_typology_population_pyramid_rules():
    """Verifies strict typology age/sex rules: FSW female-only, MSM male-only, PWID bilateral."""
    age_groups = ["Below 15", "15–19", "20–24", "25+"]
    males = [5, 10, 15, 20]
    females = [6, 12, 18, 24]

    # 1. FSW: Female only
    fig_fsw = create_population_pyramid(age_groups, males, females, population="FSW")
    assert fig_fsw.layout.height == HEIGHT_PYRAMID
    assert len(fig_fsw.data) == 1
    assert fig_fsw.data[0].name == "Female"

    # 2. MSM: Male only
    fig_msm = create_population_pyramid(age_groups, males, females, population="MSM")
    assert len(fig_msm.data) == 1
    assert fig_msm.data[0].name == "Male"

    # 3. PWID / TG / VP: Bilateral
    fig_pwid = create_population_pyramid(age_groups, males, females, population="PWID")
    assert len(fig_pwid.data) == 2
    names = {t.name for t in fig_pwid.data}
    assert names == {"Male", "Female"}


def test_treemap_generation():
    """Verifies treemap layout and height."""
    fig = create_treemap(
        labels=["Total", "Condoms", "Lubricants"],
        parents=["", "Total", "Total"],
        values=[1500, 1000, 500],
        title="Commodity Distribution",
    )
    assert fig.layout.height == HEIGHT_TREEMAP
    assert len(fig.data) == 1
    assert fig.data[0].labels[1] == "Condoms"


def test_grouped_bar_generation():
    """Verifies grouped bar generation and trace counts."""
    fig = create_grouped_bar(
        categories=["Q1", "Q2"],
        series_dict={"Screened": [100, 120], "Diagnosed": [10, 8]},
        title="STI Screening Trends",
    )
    assert len(fig.data) == 2
    assert fig.data[0].name == "Screened"


def test_extended_display_analytics_contract(mock_display_inputs: dict):
    """Verifies that compute_display_analytics pre-computes both legacy and new structures."""
    disp = compute_display_analytics(
        summary_df=mock_display_inputs["summary_df"],
        reg_analyzed=mock_display_inputs["reg_analyzed"],
        kp_analyzed=mock_display_inputs["kp_analyzed"],
        population="FSW",
        period_mode="SEM",
        total_cohort=300,
        active_kplhiv=60,
    )

    # Legacy keys
    assert "executive_metrics" in disp
    assert "hts_cascade" in disp
    assert "prep_cascade" in disp
    assert "art_cascade" in disp
    assert "clinical_cascade" in disp
    assert "commodities" in disp
    assert "demographics" in disp
    assert "geography_summary" in disp

    # Refined keys
    assert "performance_scorecard" in disp
    assert len(disp["performance_scorecard"]) == 5
    indicators = [item["indicator"] for item in disp["performance_scorecard"]]
    assert "Defined Package Coverage" in indicators
    assert "HIV Testing Coverage" in indicators

    assert "regional_performance" in disp
    assert len(disp["regional_performance"]) == 2
    regions = [r["region"] for r in disp["regional_performance"]]
    assert "COAST" in regions
    assert "NRR" in regions

    assert "sr_rankings" in disp
    assert len(disp["sr_rankings"]) == 2

    assert "management_alerts" in disp
    assert len(disp["management_alerts"]) >= 1

    assert "demographic_pyramid" in disp
    assert disp["demographic_pyramid"]["population"] == "FSW"

    assert "geography_matrix" in disp
    assert "regions" in disp["geography_matrix"]
    assert "hierarchy" in disp["geography_matrix"]


def test_pwid_demographic_pyramid_bilateral(mock_display_inputs: dict):
    """Verifies that PWID generates bilateral male and female counts from register data."""
    disp = compute_display_analytics(
        summary_df=mock_display_inputs["summary_df"],
        reg_analyzed=mock_display_inputs["reg_analyzed"],
        kp_analyzed=mock_display_inputs["kp_analyzed"],
        population="PWID",
        period_mode="SEM",
        total_cohort=300,
        active_kplhiv=60,
    )
    pyramid = disp["demographic_pyramid"]
    assert pyramid["population"] == "PWID"
    assert sum(pyramid["male_counts"]) == 2
    assert sum(pyramid["female_counts"]) == 2
