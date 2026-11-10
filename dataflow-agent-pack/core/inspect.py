"""Structure-only inspection CLI and library for DATAFLOW workbooks.

Guarantees:
- Inspects sheets, row counts, detected header skiprows, and column mapping resolution.
- NEVER outputs or prints cell values, client identifiers, or record-level data.
- Safe to run on real-world files outside the workspace.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.config_models import load_population_config
from core.exceptions import DataFlowError
from core.ingestion import (
    detect_header_skiprows,
    detect_sheet_name,
    get_workbook_sheet_names,
    load_sheet_frame,
    resolve_column_aliases,
)


def inspect_workbook(
    file_path: str | Path,
    population: str = "FSW",
    config_dir: str | Path = "config/populations",
) -> dict[str, any]:
    """Inspects workbook structure, header detection, and column mapping without printing cell values."""
    p = Path(file_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Workbook not found: {p}")

    pop_config = load_population_config(population, config_dir=config_dir)
    available_sheets = get_workbook_sheet_names(p)

    report = {
        "file_name": p.name,
        "population": population.upper(),
        "available_sheets": available_sheets,
        "sheets": {},
    }

    # Inspect Register sheet
    try:
        reg_sheet = detect_sheet_name(
            available_sheets,
            pop_config.sheet_aliases_register,
            sheet_type="Register",
        )
        reg_skiprows = detect_header_skiprows(
            p,
            reg_sheet,
            fallback_skiprows=pop_config.header_skiprows,
        )
        reg_df, rows_in, dropped_empty = load_sheet_frame(p, reg_sheet, reg_skiprows)
        raw_cols = list(reg_df.columns)

        try:
            from core.ingestion import DEFAULT_REGISTER_ALIASES, DEFAULT_REQUIRED_COLUMNS

            merged_aliases = dict(DEFAULT_REGISTER_ALIASES)
            if pop_config.column_aliases:
                merged_aliases.update(pop_config.column_aliases)
            req_cols = pop_config.required_columns or DEFAULT_REQUIRED_COLUMNS

            reg_mapping = resolve_column_aliases(
                raw_columns=raw_cols,
                alias_map=merged_aliases,
                required_columns=req_cols,
            )
            matched_cols = sorted(reg_mapping.values())
            unmatched_cols = sorted([c for c in raw_cols if c not in reg_mapping])
            missing_req = []
        except DataFlowError as exc:
            reg_mapping = {}
            matched_cols = []
            unmatched_cols = raw_cols
            missing_req = [str(exc)]

        report["sheets"]["Register"] = {
            "detected_name": reg_sheet,
            "detected_skiprows": reg_skiprows,
            "rows_in": rows_in,
            "rows_out": len(reg_df),
            "dropped_empty_rows": dropped_empty,
            "total_raw_columns": len(raw_cols),
            "matched_canonical_columns": len(matched_cols),
            "unmatched_raw_columns": len(unmatched_cols),
            "missing_required": missing_req,
            "column_names_only": {
                "matched": matched_cols,
                "unmatched": unmatched_cols,
            },
        }
    except Exception as exc:
        report["sheets"]["Register"] = {"error": str(exc)}

    # Inspect KPLHIV sheet
    kplhiv_aliases = ["KPLHIV", "KP_PLHIV", "PLHIV", "KPLHIV_Register"]
    try:
        kp_sheet = detect_sheet_name(
            available_sheets,
            kplhiv_aliases,
            sheet_type="KPLHIV",
        )
        kp_skiprows = detect_header_skiprows(p, kp_sheet, fallback_skiprows=2)
        kp_df, kp_rows_in, kp_dropped_empty = load_sheet_frame(p, kp_sheet, kp_skiprows)
        kp_raw_cols = list(kp_df.columns)

        report["sheets"]["KPLHIV"] = {
            "detected_name": kp_sheet,
            "detected_skiprows": kp_skiprows,
            "rows_in": kp_rows_in,
            "rows_out": len(kp_df),
            "dropped_empty_rows": kp_dropped_empty,
            "total_raw_columns": len(kp_raw_cols),
        }
    except Exception as exc:
        report["sheets"]["KPLHIV"] = {"error": str(exc)}

    return report


def format_inspection_report(report: dict[str, any]) -> str:
    """Formats the inspection report into a clean, human-readable structure summary."""
    lines = [
        "=" * 60,
        f"DATAFLOW WORKBOOK STRUCTURE REPORT: {report['file_name']}",
        f"Population: {report['population']}",
        f"Available Sheets ({len(report['available_sheets'])}): {', '.join(report['available_sheets'])}",
        "=" * 60,
    ]

    for sheet_type, info in report["sheets"].items():
        lines.append(f"\n--- Sheet: {sheet_type} ---")
        if "error" in info:
            lines.append(f"  Status: ERROR - {info['error']}")
            continue

        lines.append(f"  Detected Sheet Name: {info['detected_name']}")
        lines.append(f"  Detected Header Skiprows: {info['detected_skiprows']}")
        lines.append(f"  Rows Read (in): {info['rows_in']}")
        lines.append(f"  Empty Rows Dropped: {info['dropped_empty_rows']}")
        lines.append(f"  Active Rows (out): {info['rows_out']}")
        lines.append(f"  Total Columns: {info['total_raw_columns']}")

        if "matched_canonical_columns" in info:
            lines.append(f"  Matched Canonical Columns: {info['matched_canonical_columns']}")
            lines.append(f"  Unmatched Columns: {info['unmatched_raw_columns']}")
            if info["missing_required"]:
                lines.append(f"  Missing Required Columns: {info['missing_required']}")

    lines.append("\n" + "=" * 60)
    lines.append("CONFIRMATION: Zero cell values or client identifiers printed.")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DATAFLOW Structure-Only Workbook Inspector")
    parser.add_argument("file", help="Path to Excel/XLS/XLSB/CSV workbook")
    parser.add_argument("--population", default="FSW", choices=["FSW", "MSM", "PWID", "TG", "VP"])
    parser.add_argument("--config-dir", default="config/populations")
    args = parser.parse_args()

    try:
        report = inspect_workbook(args.file, population=args.population, config_dir=args.config_dir)
        print(format_inspection_report(report))
    except Exception as exc:
        print(f"Inspection error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
