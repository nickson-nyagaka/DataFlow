"""Direct code coverage measurement for Phase 5 (reporting/)."""

import ast
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

tracked_dirs = [str(BASE_DIR / "reporting")]
all_executable_lines: dict[str, set[int]] = {}
executed_lines: dict[str, set[int]] = {}

for d in tracked_dirs:
    for p in Path(d).glob("*.py"):
        if p.name == "__init__.py":
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
            stmt_lines = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.stmt) and hasattr(node, "lineno"):
                    stmt_lines.add(node.lineno)
            all_executable_lines[str(p.resolve())] = stmt_lines
            executed_lines[str(p.resolve())] = set()
        except Exception:
            pass


def trace_lines(frame, event, arg):
    if event == "line":
        fname = os.path.abspath(frame.f_code.co_filename)
        if fname in executed_lines:
            executed_lines[fname].add(frame.f_lineno)
    return trace_lines


def run_tests():
    import tests.unit.test_reporting as tr
    from tests.synthetic.generator import generate_synthetic_data

    # Fixtures
    fsw_reg, fsw_kp, _ = generate_synthetic_data("FSW", 50, 42)
    pwid_reg, pwid_kp, _ = generate_synthetic_data("PWID", 50, 42)

    tr.test_template_config_loading()
    tr.test_layout_resolution()
    tr.test_missing_geography_rows_retained((fsw_reg, fsw_kp))
    tr.test_hierarchical_sorting_with_missing_at_bottom()
    tr.test_pwid_total_nsp_sem_calculated((pwid_reg, pwid_kp))
    tr.test_excel_export_visual_formatting((fsw_reg, fsw_kp))
    tr.test_workbook_validator((fsw_reg, fsw_kp))
    tr.test_pwid_vs_non_pwid_nsp_block((fsw_reg, fsw_kp), (pwid_reg, pwid_kp))
    tr.test_dqa_exceptions_empty_table_formatting()
    tr.test_identifier_masking()
    tr.test_reporting_package_builder_multi_tab_and_zip((fsw_reg, fsw_kp))
    tr.test_all_five_populations_reopen_and_validate()
    tr.test_compare_summaries_script((fsw_reg, fsw_kp))
    tr.test_provisional_indicators_marked_in_metadata((fsw_reg, fsw_kp))
    tr.test_oracle_differential_comparison((fsw_reg, fsw_kp))
    tr.test_dqa_exceptions_populated_table()
    tr.test_cleaned_data_standalone_workbook((fsw_reg, fsw_kp))
    tr.test_template_manager_error_handling()
    tr.test_workbook_validator_corruptions((fsw_reg, fsw_kp))
    tr.test_reporting_edge_cases_and_coverage((fsw_reg, fsw_kp))


def main():
    sys.settrace(trace_lines)
    try:
        run_tests()
    finally:
        sys.settrace(None)

    total_statements = 0
    total_covered = 0

    print("=" * 70)
    print("PHASE 5 CODE COVERAGE REPORT (reporting/)")
    print("=" * 70)
    print(f"{'Module':<35} {'Executable':>10} {'Covered':>10} {'Coverage':>10}")
    print("-" * 70)

    for fpath in sorted(all_executable_lines.keys()):
        exec_set = all_executable_lines[fpath]
        cov_set = executed_lines[fpath]
        # Filter to only executable statements
        real_covered = cov_set & exec_set
        pct = (len(real_covered) / len(exec_set) * 100) if exec_set else 100.0
        rel_name = os.path.relpath(fpath, BASE_DIR)
        print(f"{rel_name:<35} {len(exec_set):>10} {len(real_covered):>10} {pct:>9.1f}%")
        total_statements += len(exec_set)
        total_covered += len(real_covered)

    print("-" * 70)
    total_pct = (total_covered / total_statements * 100) if total_statements else 100.0
    print(f"{'TOTAL':<35} {total_statements:>10} {total_covered:>10} {total_pct:>9.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
