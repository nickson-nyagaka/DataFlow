"""CLI entry point for DATAFLOW pipeline commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.cleaning import clean_kplhiv_frame, clean_register_frame
from core.config_models import load_population_config
from core.ingestion import ingest_workbook
from core.inspect import format_inspection_report, inspect_workbook
from core.validation import format_aggregate_dqa_report, run_dqa


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

    # Subcommand: run
    run_parser = subparsers.add_parser(
        "run",
        help="Run DATAFLOW pipeline execution.",
    )
    run_parser.add_argument("file", help="Path to workbook (.xlsx, .xls, .xlsb, .csv)")
    run_parser.add_argument(
        "--population",
        default="FSW",
        choices=["FSW", "MSM", "PWID", "TG", "VP"],
        help="Target population code (default: FSW)",
    )
    run_parser.add_argument(
        "--config-dir",
        default="config/populations",
        help="Path to population configurations directory",
    )
    run_parser.add_argument(
        "--aggregate-only",
        action="store_true",
        default=False,
        help="Print summary counts per rule per SR/county/region only; zero client identifiers.",
    )
    run_parser.add_argument(
        "--no-block-on-critical",
        action="store_true",
        default=False,
        help="Do not exit with error when Critical DQA exceptions exist.",
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

    elif args.command == "run":
        try:
            pop_config = load_population_config(args.population, config_dir=args.config_dir)
            p = Path(args.file)

            # 1. Ingestion
            reg_raw, kp_raw, audit = ingest_workbook(p, pop_config)

            # 2. Cleaning
            reg_clean = clean_register_frame(reg_raw)
            kp_clean = clean_kplhiv_frame(kp_raw) if not kp_raw.empty else kp_raw

            # 3. DQA Evaluation
            block_on_crit = not args.no_block_on_critical
            dqa_results = run_dqa(
                reg_clean,
                kp_clean,
                population=args.population,
                block_on_critical=block_on_crit,
            )

            # 4. Aggregate-only output
            if args.aggregate_only:
                print(
                    format_aggregate_dqa_report(
                        dqa_results, file_name=p.name, population=args.population
                    )
                )
                if dqa_results.has_critical and block_on_crit:
                    print(
                        f"\nCRITICAL DQA ALERT: {dqa_results.severity_counts.get('Critical', 0)} Critical exceptions detected.",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            else:
                print(f"DQA completed. Total exceptions: {dqa_results.total_exceptions}")

        except Exception as exc:
            print(f"Execution error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
