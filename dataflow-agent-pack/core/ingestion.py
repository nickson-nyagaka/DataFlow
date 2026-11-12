"""Multi-format workbook ingestion, sheet auto-detection, skiprows detection,
typed string loading (preserving leading zeros), and column alias resolution for DATAFLOW.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pandas as pd

from core.audit import SheetAudit, WorkbookAudit
from core.config_models import PopulationConfig
from core.exceptions import IngestionError

# Standard anchor columns used to auto-detect the header row in messy workbooks
ANCHOR_COLUMNS = {
    "kp_vp_unique_identifier_code",
    "kp_vp_unique_identifier_code_",
    "program_uic",
    "uic",
    "county",
    "region",
    "sr_name",
    "sex_m_f_",
    "sex",
    "age",
    "date_of_enrolment",
    "enrolment_date",
    "ccc_number_nupi_n_a_10_digit_number_",
    "ccc_number",
    "ccc_no_provided_by_art_centre_",
}

DEFAULT_REGISTER_ALIASES = {
    "kp_vp_unique_identifier_code": [
        "kp_vp_unique_identifier_code",
        "kp_vp_unique_identifier_code_",
        "program_uic",
        "unique_identifier_code",
        "uic",
        "client_uic",
    ],
    "county": ["county"],
    "region": ["region", "region_name", "province", "zone", "area"],
    "sr_name": [
        "sr_name",
        "sub_recipient",
        "sub_recipient_name",
        "subrecipient",
        "subrecipient_name",
        "sr",
        "implementing_partner",
        "implementing_partner_name",
        "partner",
        "partner_name",
        "cbo",
        "cbo_name",
        "ip",
        "ip_name",
        "organization",
        "agency",
        "facility",
        "site_name",
        "site",
        "dice",
        "drop_in_centre",
    ],
    "age": ["age", "age_years", "current_age"],
    "sex_m_f_": ["sex_m_f_", "sex", "gender", "sex_m_f"],
    "date_of_birth_dd_mm_yyyy_": ["date_of_birth_dd_mm_yyyy_", "dob", "date_of_birth"],
    "date_of_enrolment": [
        "date_of_enrolment",
        "enrolment_date",
        "date_enrolled",
    ],
    "peer_educator_code": ["peer_educator_code", "pe_code", "peer_educator"],
    "hiv_status_at_enrollment": [
        "hiv_status_at_enrollment",
        "hiv_status_at_enrolment",
        "baseline_hiv_status",
    ],
    "ccc_number_nupi_n_a_10_digit_number_": [
        "ccc_number_nupi_n_a_10_digit_number_",
        "ccc_number",
        "ccc_no",
        "nupi",
        "ccc_no_provided_by_art_centre_",
    ],
}

DEFAULT_REQUIRED_COLUMNS = [
    "kp_vp_unique_identifier_code",
    "county",
    "date_of_enrolment",
]


def normalize_token(text: Any) -> str:
    """Normalizes a column or sheet name for fuzzy alias matching."""
    if text is None:
        return ""
    s = str(text).strip().lower()
    # Replace all punctuation, parentheses, brackets, slashes, dashes, spaces with an underscore
    s = re.sub(r"[\s\-\./\(\)\[\]:,_]+", "_", s)
    return s.strip("_")


def get_workbook_sheet_names(file_path: Path) -> list[str]:
    """Retrieves all sheet names from an Excel file without loading data."""
    ext = file_path.suffix.lower()
    try:
        if ext != ".csv":
            try:
                from python_calamine import CalamineWorkbook

                wb = CalamineWorkbook.from_path(str(file_path))
                return wb.sheet_names
            except Exception:
                pass

        if ext in [".xlsx", ".xlsm"]:
            import openpyxl

            wb = openpyxl.load_workbook(file_path, read_only=True, keep_links=False)
            sheets = wb.sheetnames
            wb.close()
            return sheets
        elif ext == ".xlsb":
            import pyxlsb

            with pyxlsb.open_workbook(file_path) as wb:
                return wb.sheets
        elif ext == ".xls":
            import xlrd

            wb = xlrd.open_workbook(file_path, on_demand=True)
            return wb.sheet_names()
        elif ext == ".csv":
            return [file_path.stem]
        else:
            raise IngestionError(f"Unsupported file format '{ext}' for workbook: {file_path.name}")
    except IngestionError:
        raise
    except Exception as e:
        raise IngestionError(
            f"Failed to inspect sheets in '{file_path.name}': corrupted or invalid workbook ({e})"
        ) from e


def detect_sheet_name(available_sheets: list[str], aliases: list[str], sheet_type: str) -> str:
    """Finds the best matching sheet name among available sheets using configured aliases."""
    normalized_available = {normalize_token(s): s for s in available_sheets}

    for alias in aliases:
        norm_alias = normalize_token(alias)
        if norm_alias in normalized_available:
            return normalized_available[norm_alias]

    raise IngestionError(
        f"Missing required sheet: '{sheet_type}'. Looked for aliases: {aliases}. "
        f"Available sheets: {available_sheets}"
    )


def detect_header_skiprows(
    file_path: Path,
    sheet_name: str,
    max_scan_rows: int = 15,
    fallback_skiprows: int = 2,
) -> int:
    """Scans the top rows of a sheet to auto-detect where the true header row starts."""
    ext = file_path.suffix.lower()
    engine = (
        "calamine"
        if ext in [".xlsb", ".xls"]
        else ("openpyxl" if ext in [".xlsx", ".xlsm"] else None)
    )

    engine_kwargs = {"read_only": True} if engine == "openpyxl" else None
    try:
        if ext == ".csv":
            df_preview = pd.read_csv(file_path, header=None, nrows=max_scan_rows, dtype=str)
        else:
            try:
                df_preview = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=None,
                    nrows=max_scan_rows,
                    engine=engine,
                    engine_kwargs=engine_kwargs,
                    dtype=str,
                )
            except Exception:
                if engine == "openpyxl":
                    df_preview = pd.read_excel(
                        file_path,
                        sheet_name=sheet_name,
                        header=None,
                        nrows=max_scan_rows,
                        engine="calamine",
                        dtype=str,
                    )
                else:
                    raise
    except Exception as exc:
        raise IngestionError(f"Failed to read sheet preview for '{sheet_name}': {exc}") from exc

    best_row_idx = fallback_skiprows
    best_match_count = 0

    for row_idx in range(len(df_preview)):
        row_vals = [normalize_token(v) for v in df_preview.iloc[row_idx].dropna().tolist()]
        matches = sum(1 for v in row_vals if v in ANCHOR_COLUMNS)
        if matches > best_match_count:
            best_match_count = matches
            best_row_idx = row_idx

    # If we found at least 2 anchor columns, use that row; otherwise use fallback
    return best_row_idx if best_match_count >= 2 else fallback_skiprows


def resolve_column_aliases(
    raw_columns: list[str],
    alias_map: dict[str, list[str]],
    required_columns: list[str] | None = None,
) -> dict[str, str]:
    """Maps raw column names to canonical names using configuration aliases.

    Guarantees:
    - Case-insensitive, punctuation/whitespace-tolerant matching.
    - Ambiguous alias detection raises IngestionError with candidate column names (zero cell data).
    - Missing required columns raise structured IngestionError.
    """
    # 1. Build lookup from normalized alias -> canonical name
    normalized_alias_lookup: dict[str, list[str]] = {}
    for canonical, aliases in alias_map.items():
        # Every canonical name is an alias of itself
        all_aliases = set(aliases) | {canonical}
        for alias in all_aliases:
            norm_a = normalize_token(alias)
            if norm_a not in normalized_alias_lookup:
                normalized_alias_lookup[norm_a] = []
            if canonical not in normalized_alias_lookup[norm_a]:
                normalized_alias_lookup[norm_a].append(canonical)

    resolved_mapping: dict[str, str] = {}
    reverse_mapping: dict[str, list[str]] = {}

    for raw_col in raw_columns:
        norm_raw = normalize_token(raw_col)
        candidates = normalized_alias_lookup.get(norm_raw, [])

        if len(candidates) > 1:
            raise IngestionError(
                f"Ambiguous column alias: column '{raw_col}' matches multiple canonical targets: {sorted(candidates)}"
            )
        elif len(candidates) == 1:
            canonical = candidates[0]
            resolved_mapping[raw_col] = canonical
            if canonical not in reverse_mapping:
                reverse_mapping[canonical] = []
            reverse_mapping[canonical].append(raw_col)

    # Disambiguate when multiple raw columns mapped to the exact same canonical target
    duplicates = {canonical: cols for canonical, cols in reverse_mapping.items() if len(cols) > 1}
    for canonical, cols in duplicates.items():
        norm_target = normalize_token(canonical)
        scored: list[tuple[int, str]] = []
        for c in cols:
            norm_c = normalize_token(c)
            # Exact match to canonical target has highest priority
            if norm_c == norm_target:
                score = 0
            else:
                # If target represents a code/id, prefer aliases that include "code" or "id"
                target_is_code = ("code" in norm_target) or ("id" in norm_target)
                cand_has_code = ("code" in norm_c) or ("id" in norm_c)
                if target_is_code and not cand_has_code:
                    score = 20
                else:
                    score = 10
            scored.append((score, c))

        scored.sort(key=lambda x: x[0])
        min_score = scored[0][0]
        best_candidates = [c for s, c in scored if s == min_score]

        if len(best_candidates) == 1:
            best_col = best_candidates[0]
            for c in cols:
                if c != best_col:
                    del resolved_mapping[c]
        else:
            err_details = [f"canonical '{canonical}' matched by columns {sorted(best_candidates)}"]
            sep = "; "
            raise IngestionError(f"Ambiguous duplicate column mapping: {sep.join(err_details)}")

    # Check required columns if provided
    if required_columns:
        resolved_canonicals = set(resolved_mapping.values())
        missing = [req for req in required_columns if req not in resolved_canonicals]
        if missing:
            raise IngestionError(f"Missing required columns in sheet: {sorted(missing)}")

    return resolved_mapping


def load_sheet_frame(
    file_path: Path,
    sheet_name: str,
    skiprows: int,
) -> tuple[pd.DataFrame, int, int]:
    """Loads a sheet into a DataFrame with string types (preserving leading zeros) and drops 100% blank rows."""
    ext = file_path.suffix.lower()
    if ext == ".csv":
        raw_df = pd.read_csv(file_path, skiprows=skiprows, dtype=str)
    else:
        # Fast Rust-based calamine engine dramatically accelerates large files (.xlsx, .xlsb, .xls)
        try:
            raw_df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                skiprows=skiprows,
                engine="calamine",
                dtype=str,
            )
        except Exception:
            # Resilient fallback to openpyxl for xlsx/xlsm
            engine_kwargs = {"read_only": True} if ext in [".xlsx", ".xlsm"] else None
            raw_df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                skiprows=skiprows,
                engine="openpyxl" if ext in [".xlsx", ".xlsm"] else None,
                engine_kwargs=engine_kwargs,
                dtype=str,
            )

    rows_in = len(raw_df)

    # Fast vectorized blank row detection (D-010) with column-wise early exit
    non_empty_mask = pd.Series(False, index=raw_df.index)
    for col in raw_df.columns:
        s = raw_df[col]
        has_content = s.notna() & (s.astype(str).str.strip() != "")
        non_empty_mask |= has_content
        if non_empty_mask.all():
            break
    is_empty_row = ~non_empty_mask
    cleaned_df = raw_df[~is_empty_row].copy()
    dropped_empty_rows = int(is_empty_row.sum())

    return cleaned_df, rows_in, dropped_empty_rows


def ingest_workbook(
    file_path: str | Path,
    population_config: PopulationConfig,
    kplhiv_alias_map: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, WorkbookAudit]:
    """Main ingestion entry point: ingests Register and KPLHIV sheets into typed, immutable DataFrames.

    Returns:
        (register_df, kplhiv_df, workbook_audit)
    """
    p = Path(file_path).resolve()
    if not p.exists():
        raise IngestionError(f"Workbook file not found: {p}")

    file_bytes = p.read_bytes()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    audit = WorkbookAudit(
        file_path=str(p),
        population=population_config.code,
        file_sha256=file_sha256,
    )

    available_sheets = get_workbook_sheet_names(p)

    # 1. Detect Register and KPLHIV sheets (D-012)
    reg_sheet = detect_sheet_name(
        available_sheets,
        population_config.sheet_aliases_register,
        sheet_type="Register",
    )
    kplhiv_aliases = population_config.sheet_aliases_kplhiv or [
        "KPLHIV",
        "KP_PLHIV",
        "PLHIV",
        "KPLHIV_Register",
    ]
    kp_sheet = detect_sheet_name(
        available_sheets,
        kplhiv_aliases,
        sheet_type="KPLHIV",
    )

    # 2. Auto-detect header skiprows
    reg_skiprows = detect_header_skiprows(
        p,
        reg_sheet,
        fallback_skiprows=population_config.header_skiprows,
    )
    kp_skiprows = detect_header_skiprows(
        p,
        kp_sheet,
        fallback_skiprows=2,
    )

    # 3. Load sheets with string preservation (D-010)
    reg_df, reg_rows_in, reg_dropped_empty = load_sheet_frame(p, reg_sheet, reg_skiprows)
    kp_df, kp_rows_in, kp_dropped_empty = load_sheet_frame(p, kp_sheet, kp_skiprows)

    # 4. Resolve column aliases
    from core.template_schema import build_register_template_mapping

    merged_reg_aliases = dict(DEFAULT_REGISTER_ALIASES)
    if population_config.column_aliases:
        merged_reg_aliases.update(population_config.column_aliases)

    required_cols = population_config.required_columns or DEFAULT_REQUIRED_COLUMNS

    reg_mapping = build_register_template_mapping(
        raw_columns=list(reg_df.columns),
        alias_map=merged_reg_aliases,
        required_columns=required_cols,
    )
    reg_df = reg_df.rename(columns=reg_mapping)

    # KPLHIV column mapping
    kp_default_aliases = {
        "kp_vp_unique_identifier_code": [
            "program_uic",
            "uic",
            "kp_vp_unique_identifier_code",
            "client_uic",
        ],
        "ccc_number_nupi_n_a_10_digit_number_": [
            "ccc_no_provided_by_art_centre_",
            "ccc_number",
            "ccc_no",
            "nupi",
        ],
        "county": ["county"],
        "sr_name": [
            "sr_name",
            "sub_recipient",
            "sub_recipient_name",
            "subrecipient",
            "subrecipient_name",
            "sr",
            "implementing_partner",
            "implementing_partner_name",
            "partner",
            "partner_name",
            "cbo",
            "cbo_name",
            "ip",
            "ip_name",
            "facility",
            "site",
        ],
        "region": ["region", "region_name", "province", "zone", "area"],
        "sub_county": ["sub_county"],
        "ward": ["ward"],
        "sex_m_f_": ["sex", "gender", "sex_m_f_"],
        "age": ["age", "age_years"],
    }
    kp_map = kplhiv_alias_map or kp_default_aliases
    kp_mapping = resolve_column_aliases(
        raw_columns=list(kp_df.columns),
        alias_map=kp_map,
        required_columns=["kp_vp_unique_identifier_code"] if not kp_df.empty else None,
    )

    # Map primary viral load column (Levels copies/ml) on KPLHIV sheet if present
    for raw_col in kp_df.columns:
        norm = normalize_token(raw_col)
        if "levels_copies_ml" in norm or norm == "levels" or "viral_load" in norm:
            if "levels_copies_ml_" not in kp_mapping.values():
                kp_mapping[raw_col] = "levels_copies_ml_"
                break

    kp_df = kp_df.rename(columns=kp_mapping)

    # 5. Populate and verify audit records
    reg_audit = SheetAudit(
        sheet_name=reg_sheet,
        rows_in=reg_rows_in,
        rows_out=len(reg_df),
        dropped_empty_rows=reg_dropped_empty,
        detected_skiprows=reg_skiprows,
        input_sha256=WorkbookAudit.compute_frame_hash(reg_df),
    )
    audit.add_sheet_audit(reg_audit)

    kp_audit = SheetAudit(
        sheet_name=kp_sheet,
        rows_in=kp_rows_in,
        rows_out=len(kp_df),
        dropped_empty_rows=kp_dropped_empty,
        detected_skiprows=kp_skiprows,
        input_sha256=WorkbookAudit.compute_frame_hash(kp_df),
    )
    audit.add_sheet_audit(kp_audit)

    return reg_df, kp_df, audit
