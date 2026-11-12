"""Dataframe cleaning pipeline for DATAFLOW.

Implements:
1. Pure, non-mutating transformation (input DataFrame remains 100% byte-for-byte immutable).
2. Whitespace trimming and multiple space collapse.
3. Controlled vocabulary case normalization without silent coercion (D-008).
4. Strict preservation of leading zeros and stripping of false trailing '.0' on IDs.
5. Robust Day-First date parsing with Excel serial number fallbacks (D-011).
6. Missing Sub-Recipient retention with 'Unknown' sentinel (D-009).
7. Numeric age conversion preserving NaNs (D-003).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def clean_string_series(series: pd.Series) -> pd.Series:
    """Strips leading/trailing whitespace and collapses internal multiple spaces."""
    if not (series.dtype == "object" or pd.api.types.is_string_dtype(series)):
        return series

    s = series.astype(str).str.strip()
    if s.str.contains(r"\s{2,}", regex=True).any():
        s = s.str.replace(r"\s+", " ", regex=True)
    mask = series.isna() | s.str.lower().isin(["nan", "none", ""])
    return s.mask(mask, np.nan)


def normalize_vocabulary_series(
    series: pd.Series,
    case_variants: dict[str, str],
) -> pd.Series:
    """Normalizes known case variants of controlled vocabulary without coercing unrecognised values.

    Guarantees:
    - Known variants are mapped to canonical case (e.g. 'known positive' -> 'Known Positive').
    - Unrecognised values (e.g. 'Positve', 'RandomText') are preserved untouched in the Series
      so that downstream DQA validation rules can flag them as exceptions.
    """
    lookup = {k.strip().lower(): v for k, v in case_variants.items()}
    s_clean = series.astype(str).str.strip()
    s_lower = s_clean.str.lower()
    mapped = s_lower.map(lookup)
    result = mapped.combine_first(s_clean)
    mask = series.isna() | s_clean.str.lower().isin(["nan", "none", ""])
    return result.mask(mask, np.nan)


def clean_numeric_id_series(series: pd.Series) -> pd.Series:
    """Removes erroneous float trailing '.0' added by Excel while strictly preserving leading zeros."""
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0+$", "", regex=True)
    mask = series.isna() | s.str.lower().isin(["nan", "none", ""])
    return s.mask(mask, np.nan)


def parse_date_series(series: pd.Series) -> pd.Series:
    """Parses dates using Day-First (DD/MM/YYYY) convention with Excel serial number fallbacks (D-011).

    Unparseable strings become NaT/NaN without crashing.
    """
    s = series.astype(str).str.strip()
    mask_empty = series.isna() | s.str.lower().isin(["nan", "none", ""])

    # 1. Try ISO date parsing first for speed (YYYY-MM-DD)
    is_iso = s.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    dt_iso = pd.to_datetime(s[is_iso], format="%Y-%m-%d", errors="coerce")

    # 2. For remaining non-ISO non-empty values, try dayfirst=True
    non_iso = ~is_iso & ~mask_empty
    dt_dayfirst = pd.to_datetime(s[non_iso], dayfirst=True, errors="coerce")

    # 3. For any remaining values that failed, check if numeric serial (e.g. 45123)
    failed = dt_dayfirst.isna()
    if failed.any():
        failed_s = s[non_iso][failed]
        is_num = failed_s.str.replace(r"\.0+$", "", regex=True).str.isdigit()
        if is_num.any():
            serials = pd.to_numeric(failed_s[is_num], errors="coerce")
            dt_serials = pd.to_datetime(serials, unit="D", origin="1899-12-30", errors="coerce")
            dt_dayfirst = dt_dayfirst.combine_first(dt_serials)

    # Combine ISO and dayfirst results
    combined_dt = pd.Series(pd.NaT, index=series.index)
    if is_iso.any():
        combined_dt.update(dt_iso)
    if non_iso.any():
        combined_dt.update(dt_dayfirst)

    result_str = combined_dt.dt.strftime("%Y-%m-%d")
    return result_str.mask(mask_empty | combined_dt.isna(), np.nan)


def clean_register_frame(
    df: pd.DataFrame,
    vocabularies: dict[str, dict[str, str]] | None = None,
) -> pd.DataFrame:
    """Cleans a Register DataFrame without modifying the input frame in place.

    Guarantees:
    - Input DataFrame remains 100% immutable.
    - All string columns stripped of extraneous whitespace.
    - IDs (UIC, CCC, PE codes) cleaned of trailing '.0' and leading zeros preserved.
    - Missing sr_name assigned to 'Unknown' per D-009 (zero rows dropped).
    - Dates parsed to YYYY-MM-DD strings with dayfirst=True per D-011.
    - Controlled vocabularies normalized per D-008.
    """
    cleaned = df.copy(deep=True)

    # 1. Clean whitespace across all string columns
    for col in cleaned.columns:
        cleaned[col] = clean_string_series(cleaned[col])

    # 2. Clean IDs (preserve leading zeros, strip trailing .0)
    id_cols = [
        "kp_vp_unique_identifier_code",
        "ccc_number_nupi_n_a_10_digit_number_",
        "peer_educator_code",
    ]
    for col in id_cols:
        if col in cleaned.columns:
            cleaned[col] = clean_numeric_id_series(cleaned[col])

    # 3. Handle missing Sub-Recipient (sr_name) per D-009
    if "sr_name" in cleaned.columns:
        cleaned["sr_name"] = cleaned["sr_name"].fillna("Unknown")
    else:
        cleaned["sr_name"] = "Unknown"

    # 4. Parse Dates (enrolment, DOB, visit dates) per D-011
    date_cols = [
        col
        for col in cleaned.columns
        if any(token in col.lower() for token in ["date", "dob", "enrolment"])
    ]
    for col in date_cols:
        cleaned[col] = parse_date_series(cleaned[col])

    # 5. Normalize Age per D-003 (never default; coerce invalid to NaN)
    if "age" in cleaned.columns:
        cleaned["age"] = pd.to_numeric(cleaned["age"], errors="coerce")

    # 6. Apply Controlled Vocabularies
    if vocabularies:
        # HIV Status
        hiv_variants = vocabularies.get("hiv_status", {})
        if hiv_variants and "hiv_status_at_enrollment" in cleaned.columns:
            cleaned["hiv_status_at_enrollment"] = normalize_vocabulary_series(
                cleaned["hiv_status_at_enrollment"], hiv_variants
            )

        # PrEP Status columns (e.g. prep_status_1, prep_status_2, etc.)
        prep_variants = vocabularies.get("prep_status", {})
        if prep_variants:
            for col in cleaned.columns:
                if "prep_status" in col.lower():
                    cleaned[col] = normalize_vocabulary_series(cleaned[col], prep_variants)

        # Yes/No columns
        yes_no_variants = vocabularies.get("yes_no", {})
        if yes_no_variants:
            yn_patterns = ["art", "tb_screened", "sti_screened", "diagnosed", "presumed"]
            for col in cleaned.columns:
                if any(p in col.lower() for p in yn_patterns):
                    cleaned[col] = normalize_vocabulary_series(cleaned[col], yes_no_variants)

    return cleaned


def clean_kplhiv_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans a KPLHIV DataFrame without modifying the input frame in place."""
    cleaned = df.copy(deep=True)

    for col in cleaned.columns:
        cleaned[col] = clean_string_series(cleaned[col])

    id_cols = [
        "kp_vp_unique_identifier_code",
        "ccc_number_nupi_n_a_10_digit_number_",
    ]
    for col in id_cols:
        if col in cleaned.columns:
            cleaned[col] = clean_numeric_id_series(cleaned[col])

    if "age" in cleaned.columns:
        cleaned["age"] = pd.to_numeric(cleaned["age"], errors="coerce")

    return cleaned
