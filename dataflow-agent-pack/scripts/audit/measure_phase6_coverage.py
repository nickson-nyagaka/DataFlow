"""Direct code coverage measurement for Phase 6 (ui/, core/override.py, core/runner.py, app.py)."""

import ast
import os
import sys
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

tracked_files = [
    BASE_DIR / "app.py",
    BASE_DIR / "core" / "override.py",
    BASE_DIR / "core" / "runner.py",
]
for p in (BASE_DIR / "ui").glob("*.py"):
    if p.name != "__init__.py":
        tracked_files.append(p)

all_executable_lines: dict[str, set[int]] = {}
executed_lines: dict[str, set[int]] = {}

for p in tracked_files:
    if not p.exists():
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
    import pytest

    # Run the unit tests under trace
    pytest.main(
        [
            str(BASE_DIR / "tests" / "unit" / "test_override.py"),
            str(BASE_DIR / "tests" / "unit" / "test_ui.py"),
            "-q",
        ]
    )


if __name__ == "__main__":
    old_trace = sys.gettrace()
    sys.settrace(trace_lines)
    threading.settrace(trace_lines)
    try:
        run_tests()
    finally:
        sys.settrace(old_trace)
        threading.settrace(None)

    print("=" * 70)
    print("PHASE 6 CODE COVERAGE REPORT (ui/, core/override.py, core/runner.py, app.py)")
    print("=" * 70)
    print(f"{'Module':<40} {'Executable':>10} {'Covered':>10} {'Coverage':>10}")
    print("-" * 70)

    total_exec = 0
    total_cov = 0
    for fpath in sorted(all_executable_lines.keys()):
        exec_count = len(all_executable_lines[fpath])
        cov_count = len(executed_lines[fpath].intersection(all_executable_lines[fpath]))
        total_exec += exec_count
        total_cov += cov_count
        rel = os.path.relpath(fpath, str(BASE_DIR))
        pct = (cov_count / exec_count * 100) if exec_count > 0 else 100.0
        print(f"{rel:<40} {exec_count:>10} {cov_count:>10} {pct:>9.1f}%")

    print("-" * 70)
    tot_pct = (total_cov / total_exec * 100) if total_exec > 0 else 100.0
    print(f"{'TOTAL':<40} {total_exec:>10} {total_cov:>10} {tot_pct:>9.1f}%")
    print("=" * 70)
