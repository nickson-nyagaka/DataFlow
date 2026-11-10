"""Unit tests for Viral Load parsing, standardization, and suppression."""

from __future__ import annotations

import numpy as np
import pytest

from analytics.viral_load import (
    is_viral_load_suppressed,
    parse_and_standardize_viral_load,
)
from core.compat import CompatSwitches


@pytest.mark.parametrize(
    "raw,expected_modern,expected_legacy",
    [
        ("LDL", "LDL", "LDL"),
        ("<LDL", "LDL", "LDL"),
        ("<ldl", "LDL", "LDL"),
        (">LDL", "UNKNOWN", "LDL"),  # D-025 unparseable in modern mode, LDL in legacy mode
        (">ldl", "UNKNOWN", "LDL"),
        ("<200", 50, 200),  # Suppressed (<200) in modern mode; 200 (unsuppressed) in legacy regex
        ("< 200", 50, 200),
        (">200", 250, 200),  # Unsuppressed in modern mode
        ("> 200", 250, 200),
        ("200", 200, 200),
        ("50", 50, 50),
        ("1,200", 1200, 1200),
        ("100,000", 100000, 100000),
        ("9250cp/ml", 9250, 9250),
        ("450 copies/ml", 450, 450),
        ("Target Not Detected", "UNKNOWN", "UNKNOWN"),
        ("", "UNKNOWN", "UNKNOWN"),
        ("   ", "UNKNOWN", "UNKNOWN"),
        (np.nan, "UNKNOWN", "UNKNOWN"),
        (None, "UNKNOWN", "UNKNOWN"),
        ("invalid junk string", "UNKNOWN", "UNKNOWN"),
    ],
)
def test_parse_and_standardize_viral_load(raw, expected_modern, expected_legacy):
    modern_compat = CompatSwitches.all_disabled()
    legacy_compat = CompatSwitches.all_enabled()

    assert parse_and_standardize_viral_load(raw, compat=modern_compat) == expected_modern
    assert parse_and_standardize_viral_load(raw, compat=legacy_compat) == expected_legacy


@pytest.mark.parametrize(
    "standardized,suppressed",
    [
        ("LDL", True),
        (50, True),
        (199, True),
        (0, True),
        (200, False),  # 200 copies/ml threshold is NOT suppressed (< 200 required)
        (250, False),
        (1200, False),
        ("UNKNOWN", False),
        (None, False),
        (np.nan, False),
    ],
)
def test_is_viral_load_suppressed(standardized, suppressed):
    assert is_viral_load_suppressed(standardized) is suppressed
