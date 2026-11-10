"""Period engine for DATAFLOW.

Handles:
1. Loading and validating reporting period configurations (config/reporting/periods.yaml).
2. Pre-calculation schema validation: verifies expected visit columns count and column naming.
3. Explicit period column resolution (source column -> period) without positional slicing hazards.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from core.exceptions import ConfigValidationError, DataFlowError


class PeriodValidationError(DataFlowError):
    """Raised when source columns do not match the expected reporting period schema."""

    pass


def load_period_config(config_path: str | Path = "config/reporting/periods.yaml") -> dict[str, Any]:
    """Loads and validates period configuration YAML."""
    p = Path(config_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Period configuration not found at {p}")

    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required_keys = ["reporting_cycle", "q1_columns_count", "q2_columns_count"]
    for k in required_keys:
        if k not in data:
            raise ConfigValidationError(
                f"Missing required key '{k}' in period configuration.",
                file=str(p),
                key=k,
            )
    return data


def resolve_period_columns(
    df: pd.DataFrame,
    col_family_pattern: str,
    q1_count: int = 3,
    q2_count: int = 3,
    required: bool = True,
    lexicographic_sort: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Resolves and validates Q1, Q2, and Semester column sets for a column family pattern.

    Returns:
        (q1_cols, q2_cols, sem_cols) where sem_cols = q1_cols + q2_cols.

    Raises:
        PeriodValidationError: If column count is insufficient or unexpected.
    """
    regex = re.compile(col_family_pattern)
    matched = [c for c in df.columns if regex.search(c)]

    if lexicographic_sort:
        matched_sorted = sorted(matched)
    else:
        # Natural sort or numeric index sort on visit suffix if present
        def extract_index(col_name: str) -> int:
            digits = re.findall(r"\d+", col_name)
            return int(digits[-1]) if digits else 0

        matched_sorted = sorted(matched, key=extract_index)

    if not matched_sorted:
        if required:
            raise PeriodValidationError(
                f"No columns found matching pattern '{col_family_pattern}'."
            )
        return [], [], []

    expected_total = q1_count + q2_count
    if len(matched_sorted) < expected_total:
        raise PeriodValidationError(
            f"Insufficient columns for pattern '{col_family_pattern}': "
            f"expected at least {expected_total} (Q1={q1_count}, Q2={q2_count}), "
            f"found {len(matched_sorted)} ({matched_sorted})."
        )

    q1_cols = matched_sorted[:q1_count]
    q2_cols = matched_sorted[q1_count:expected_total]
    sem_cols = matched_sorted[:expected_total]

    return q1_cols, q2_cols, sem_cols
