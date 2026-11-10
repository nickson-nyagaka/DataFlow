"""CLI entry point for DATAFLOW pipeline commands."""

from __future__ import annotations

import argparse
import sys

from core.inspect import format_inspection_report, inspect_workbook


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="python -m core.pipeline",
        description="DATAFLOW pipeline command line interface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: inspect
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect workbook structure without outputting cell data or client identifiers.",
    )
    inspect_parser.add_argument("file", help="Path to workbook (.xlsx, .xls, .xlsb, .csv)")
    inspect_parser.add_argument(
        "--population",
        default="FSW",
        choices=["FSW", "MSM", "PWID", "TG", "VP"],
        help="Target population code (default: FSW)",
    )
    inspect_parser.add_argument(
        "--config-dir",
        default="config/populations",
        help="Path to population configurations directory",
    )

    args = parser.parse_args(argv)

    if args.command == "inspect":
        try:
            report = inspect_workbook(
                args.file,
                population=args.population,
                config_dir=args.config_dir,
            )
            print(format_inspection_report(report))
        except Exception as exc:
            print(f"Inspection error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
