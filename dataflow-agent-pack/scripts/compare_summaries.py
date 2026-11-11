"""Summary workbook comparison CLI tool (aggregate-only delta reporter)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import openpyxl


def compare_summary_workbooks(
    file1: Path | str,
    file2: Path | str,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """
    Compares two summary workbooks cell-by-cell and computes aggregate delta metrics.

    Guarantees privacy: never prints client identifiers or row-level records.
    """
    p1 = Path(file1)
    p2 = Path(file2)

    if not p1.is_file():
        raise FileNotFoundError(f"File 1 not found: {p1}")
    if not p2.is_file():
        raise FileNotFoundError(f"File 2 not found: {p2}")

    wb1 = openpyxl.load_workbook(p1, data_only=False)
    wb2 = openpyxl.load_workbook(p2, data_only=False)

    sheets1 = set(wb1.sheetnames)
    sheets2 = set(wb2.sheetnames)

    common_sheets = sorted(sheets1 & sheets2)
    target_sheets = [sheet_name] if sheet_name else common_sheets

    report = {
        "file1": str(p1),
        "file2": str(p2),
        "common_sheets": common_sheets,
        "sheets_only_in_file1": list(sheets1 - sheets2),
        "sheets_only_in_file2": list(sheets2 - sheets1),
        "sheet_comparisons": {},
        "identical": True,
    }

    for sname in target_sheets:
        if sname not in wb1.sheetnames or sname not in wb2.sheetnames:
            continue

        ws1 = wb1[sname]
        ws2 = wb2[sname]

        max_row = max(ws1.max_row, ws2.max_row)
        max_col = max(ws1.max_column, ws2.max_column)

        total_cells = 0
        diff_cells = 0
        diff_by_column: dict[int, int] = {}
        diff_samples: list[dict[str, Any]] = []

        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                total_cells += 1
                v1 = ws1.cell(row=r, column=c).value
                v2 = ws2.cell(row=r, column=c).value

                str_v1 = str(v1).strip() if v1 is not None else ""
                str_v2 = str(v2).strip() if v2 is not None else ""

                if str_v1 != str_v2:
                    diff_cells += 1
                    diff_by_column[c] = diff_by_column.get(c, 0) + 1
                    report["identical"] = False
                    if len(diff_samples) < 5:
                        diff_samples.append(
                            {
                                "row": r,
                                "col": c,
                                "file1_val": str_v1,
                                "file2_val": str_v2,
                            }
                        )

        report["sheet_comparisons"][sname] = {
            "total_cells_checked": total_cells,
            "differing_cells": diff_cells,
            "differences_by_column_index": diff_by_column,
            "sample_deltas": diff_samples,
        }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="DATAFLOW Summary Workbook Comparison Tool")
    parser.add_argument("file1", help="Path to first Excel workbook")
    parser.add_argument("file2", help="Path to second Excel workbook")
    parser.add_argument("--sheet", help="Specific sheet name to compare", default=None)

    args = parser.parse_args()

    try:
        res = compare_summary_workbooks(args.file1, args.file2, sheet_name=args.sheet)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("=" * 70)
    print("DATAFLOW SUMMARY WORKBOOK COMPARISON REPORT (AGGREGATE-ONLY)")
    print("=" * 70)
    print(f"File 1: {res['file1']}")
    print(f"File 2: {res['file2']}")
    print(f"Common Sheets: {', '.join(res['common_sheets'])}")
    if res["sheets_only_in_file1"]:
        print(f"Sheets only in File 1: {', '.join(res['sheets_only_in_file1'])}")
    if res["sheets_only_in_file2"]:
        print(f"Sheets only in File 2: {', '.join(res['sheets_only_in_file2'])}")

    print("-" * 70)
    for sname, sdata in res["sheet_comparisons"].items():
        diff_count = sdata["differing_cells"]
        total_count = sdata["total_cells_checked"]
        status = "MATCH" if diff_count == 0 else f"DIFF ({diff_count} cells differ)"
        print(f"Sheet '{sname}': {status} (Total cells: {total_count})")
        if diff_count > 0:
            print("  Differing cells per column index:")
            for col_idx, cnt in sdata["differences_by_column_index"].items():
                print(f"    Col {col_idx}: {cnt} difference(s)")

    print("=" * 70)
    if res["identical"]:
        print("RESULT: WORKBOOKS ARE IDENTICAL.")
        return 0
    else:
        print("RESULT: DIFFERENCES DETECTED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
