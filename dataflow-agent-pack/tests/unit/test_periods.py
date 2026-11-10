"""Unit tests for Period Engine (core/periods.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from core.periods import (
    PeriodValidationError,
    load_period_config,
    resolve_period_columns,
)


def test_load_period_config():
    cfg = load_period_config("config/reporting/periods.yaml")
    assert "Jul-Dec 2026" in cfg["reporting_cycle"]
    assert cfg["q1_columns_count"] == 3
    assert cfg["q2_columns_count"] == 3


def test_load_period_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_period_config("nonexistent/periods.yaml")


def test_resolve_period_columns_numeric_sort():
    # 10 visits: verify visit_10 is placed last in numeric sort
    cols = [f"prep_status_{i}" for i in range(1, 11)]
    df = pd.DataFrame(columns=cols)

    q1, q2, sem = resolve_period_columns(df, r"prep_status_?\d*$", q1_count=3, q2_count=3)
    assert q1 == ["prep_status_1", "prep_status_2", "prep_status_3"]
    assert q2 == ["prep_status_4", "prep_status_5", "prep_status_6"]
    assert sem == q1 + q2


def test_resolve_period_columns_lexicographic_sort():
    cols = [f"prep_status_{i}" for i in range(1, 11)]
    df = pd.DataFrame(columns=cols)

    q1, q2, sem = resolve_period_columns(
        df, r"prep_status_?\d*$", q1_count=3, q2_count=3, lexicographic_sort=True
    )
    # In string sort, prep_status_10 comes before prep_status_2
    assert q1 == ["prep_status_1", "prep_status_10", "prep_status_2"]
    assert q2 == ["prep_status_3", "prep_status_4", "prep_status_5"]


def test_resolve_period_columns_insufficient_columns():
    cols = ["prep_status_1", "prep_status_2", "prep_status_3"]
    df = pd.DataFrame(columns=cols)

    with pytest.raises(PeriodValidationError) as exc_info:
        resolve_period_columns(df, r"prep_status_?\d*$", q1_count=3, q2_count=3)
    assert "Insufficient columns" in str(exc_info.value)


def test_resolve_period_columns_missing_pattern():
    df = pd.DataFrame(columns=["col_a", "col_b"])
    with pytest.raises(PeriodValidationError):
        resolve_period_columns(df, r"nonexistent_pattern_\d*$", required=True)

    # Optional should return empty lists without raising
    q1, q2, sem = resolve_period_columns(df, r"nonexistent_pattern_\d*$", required=False)
    assert q1 == []
    assert q2 == []
    assert sem == []
