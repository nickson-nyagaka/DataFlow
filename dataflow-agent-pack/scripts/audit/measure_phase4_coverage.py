"""Direct code coverage measurement for Phase 4 (core/ and analytics/)."""

import ast
import os
import pathlib
import sys

BASE_DIR = Path = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

tracked_dirs = [str(BASE_DIR / "core"), str(BASE_DIR / "analytics")]
all_executable_lines = {}
executed_lines = {}

# Discover statement lines using AST
for d in tracked_dirs:
    for p in pathlib.Path(d).glob("*.py"):
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
    # Import and run test functions directly
    import tests.unit.test_analytics as ta
    import tests.unit.test_periods as tp
    import tests.unit.test_viral_load as tvl

    # Periods
    tp.test_load_period_config()
    try:
        tp.test_load_period_config_missing_file()
    except Exception:
        pass
    tp.test_resolve_period_columns_numeric_sort()
    tp.test_resolve_period_columns_lexicographic_sort()
    try:
        tp.test_resolve_period_columns_insufficient_columns()
    except Exception:
        pass
    tp.test_resolve_period_columns_missing_pattern()

    # Viral load
    for raw, exp_m, exp_l in [
        ("LDL", "LDL", "LDL"),
        ("<LDL", "LDL", "LDL"),
        (">LDL", "UNKNOWN", "LDL"),
        ("<200", 50, 200),
        (">200", 250, 200),
        ("200", 200, 200),
        ("1,200", 1200, 1200),
        ("9250cp/ml", 9250, 9250),
        ("", "UNKNOWN", "UNKNOWN"),
        ("invalid", "UNKNOWN", "UNKNOWN"),
    ]:
        tvl.test_parse_and_standardize_viral_load(raw, exp_m, exp_l)

    for val, supp in [
        ("LDL", True),
        (50, True),
        (199, True),
        (200, False),
        (250, False),
        ("UNKNOWN", False),
    ]:
        tvl.test_is_viral_load_suppressed(val, supp)

    # Analytics tests
    ta.test_stage_a_oracle_parity_from_fixtures("FSW", ta.FIXTURES_DIR / "synthetic_fsw.xlsx")
    ta.test_stage_a_oracle_parity_from_fixtures("PWID", ta.FIXTURES_DIR / "synthetic_pwid.xlsx")
    for pop in ["MSM", "TG", "VP"]:
        ta.test_stage_a_oracle_parity_generated_populations(pop)

    ta.test_switch_legacy_missing_age_below_15()
    ta.test_switch_legacy_row_sum_flags()
    ta.test_switch_legacy_hts_sem_month_ge_7()
    ta.test_switch_legacy_comment_out_pwid_nsp()
    ta.test_switch_legacy_capitalize_vocabulary()
    ta.test_switch_legacy_lexicographic_column_sort()

    for pop in ["FSW", "MSM", "PWID", "TG", "VP"]:
        ta.test_defined_package_all_components_present_general_pathway(pop)

    for comp in ["hts_q1", "sti_screened_q1", "tb_screened_q1", "condoms_q1", "he_rrc_q1"]:
        ta.test_defined_package_general_pathway_missing_single_component(comp)

    ta.test_defined_package_plhiv_service_pathway_without_hts()
    ta.test_defined_package_multi_row_uic_encounter_aggregation()


def main():
    sys.settrace(trace_lines)
    run_tests()
    sys.settrace(None)

    total_exec = 0
    total_all = 0
    print("\n" + "=" * 55)
    print("PHASE 4 CODE COVERAGE REPORT (core/ and analytics/)")
    print("=" * 55)

    analytics_exec = 0
    analytics_all = 0

    for f, stmts in sorted(all_executable_lines.items()):
        bname = os.path.basename(f)
        covered = executed_lines[f] & stmts
        pct = (len(covered) / len(stmts) * 100) if stmts else 100
        total_exec += len(covered)
        total_all += len(stmts)
        if "analytics" in f:
            analytics_exec += len(covered)
            analytics_all += len(stmts)
        print(f"{bname:30s}: {len(covered):3d} / {len(stmts):3d} ({pct:5.1f}%)")

    total_pct = (total_exec / total_all * 100) if total_all else 100
    analytics_pct = (analytics_exec / analytics_all * 100) if analytics_all else 100

    print("-" * 55)
    print(f"ANALYTICS/ COVERAGE : {analytics_exec}/{analytics_all} ({analytics_pct:.1f}%)")
    print(f"TOTAL CODE COVERAGE : {total_exec}/{total_all} ({total_pct:.1f}%)")
    print("=" * 55)


if __name__ == "__main__":
    main()
