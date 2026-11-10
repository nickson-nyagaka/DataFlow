"""Viral Load parsing, standardization, and suppression evaluation for DATAFLOW."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from core.compat import CompatSwitches


def parse_and_standardize_viral_load(
    val: Any,
    compat: CompatSwitches | None = None,
) -> int | str:
    """Parses and standardizes raw viral load copies/ml string into integer or sentinel string.

    Handles:
    - 'LDL', '<LDL' -> 'LDL'
    - '>LDL' -> 'LDL' in legacy mode, 'UNKNOWN' in modern mode (D-025)
    - '<200' -> 200 (unsuppressed int) in legacy mode; 50 (suppressed) in modern mode
    - '>200' -> 250 (numeric unsuppressed)
    - Comma numbers ('1,200' -> 1200)
    - Copies/ml strings ('9250cp/ml' -> 9250)
    - Blanks, NaNs, junk strings -> 'UNKNOWN'
    """
    if pd.isna(val):
        return "UNKNOWN"

    v = str(val).strip().lower()
    if not v or v in ["nan", "none", "n/a", ""]:
        return "UNKNOWN"

    legacy_mode = compat.legacy_capitalize_vocabulary if compat else False

    if legacy_mode:
        # Exact legacy regex: [<>]?ldl
        if re.fullmatch(r"[<>]?ldl", v):
            return "LDL"
        match = re.search(r"[\d,]+", v)
        if match:
            try:
                return int(match.group().replace(",", ""))
            except ValueError:
                return "UNKNOWN"
        return "UNKNOWN"

    # Modern mode (D-025)
    if v in ["ldl", "<ldl"]:
        return "LDL"

    if v == ">ldl":
        return "UNKNOWN"

    if re.fullmatch(r"<\s*200", v):
        return 50  # Suppressed below detection threshold (<200)

    if re.fullmatch(r">\s*200", v):
        return 250  # Unsuppressed above threshold (>200)

    # Extract digits with optional commas
    match = re.search(r"\d[\d,]*", v)
    if match:
        try:
            return int(match.group().replace(",", ""))
        except ValueError:
            return "UNKNOWN"

    return "UNKNOWN"


def is_viral_load_suppressed(standardized_val: Any) -> bool:
    """Evaluates whether a standardized viral load indicates viral suppression (< 200 copies/ml or LDL)."""
    if standardized_val == "LDL":
        return True
    if isinstance(standardized_val, (int, float)) and standardized_val < 200:
        return True
    return False
