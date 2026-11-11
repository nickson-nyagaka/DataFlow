#!/usr/bin/env python3
"""Detailed structural diff and comparison of cells 75, 77, 80, 82."""

import difflib
import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)


def get_cell(idx):
    for c in cells:
        if c["index"] == idx:
            return c["source"]
    return None


c75 = get_cell(75)
c77 = get_cell(77)
c80 = get_cell(80)
c82 = get_cell(82)

# Compare 75 vs 77 (Q1 non-PWID vs Q1 PWID)
diff_75_77 = list(
    difflib.unified_diff(
        c75.splitlines(),
        c77.splitlines(),
        fromfile="Cell 75 (Q1 non-PWID)",
        tofile="Cell 77 (Q1 PWID)",
        lineterm="",
    )
)

print(f"Diff 75 vs 77: {len(diff_75_77)} lines")
for line in diff_75_77[:30]:
    print(line)

# Compare 80 vs 82 (Q1/Q2/SEM non-PWID vs Q1/Q2/SEM PWID)
diff_80_82 = list(
    difflib.unified_diff(
        c80.splitlines(),
        c82.splitlines(),
        fromfile="Cell 80 (Full non-PWID)",
        tofile="Cell 82 (Full PWID)",
        lineterm="",
    )
)
print(f"\nDiff 80 vs 82: {len(diff_80_82)} lines")
for line in diff_80_82[:30]:
    print(line)

# Compare 75 vs 80 (Q1 non-PWID vs Full non-PWID)
diff_75_80 = list(
    difflib.unified_diff(
        c75.splitlines(),
        c80.splitlines(),
        fromfile="Cell 75 (Q1 non-PWID)",
        tofile="Cell 80 (Full non-PWID)",
        lineterm="",
    )
)
print(f"\nDiff 75 vs 80: {len(diff_75_80)} lines")
for line in diff_75_80[:30]:
    print(line)
