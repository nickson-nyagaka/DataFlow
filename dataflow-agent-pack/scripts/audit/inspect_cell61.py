#!/usr/bin/env python3
"""Extract every indicator and logic from Cell 61."""

import json
import re
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)

c61 = next(c for c in cells if c["index"] == 61)["source"]

lines = c61.splitlines()
print(f"Cell 61 lines: {len(lines)}")

# Let's inspect sections in Cell 61
current_section = None
sections = {}
for i, line in enumerate(lines):
    if line.strip().startswith("# =="):
        # next line might be title
        pass
    elif line.strip().startswith("# ") and any(
        k in line
        for k in [
            "PrEP",
            "HIV",
            "ART",
            "STI",
            "TB",
            "Condoms",
            "Defined",
            "NSP",
            "Active",
            "HTS",
            "Commodity",
            "indicators",
        ]
    ):
        current_section = line.strip()
        sections[current_section] = []
    elif current_section:
        sections[current_section].append((i + 1, line))

print("Sections found:")
for sec, sec_lines in sections.items():
    print(f"- {sec} ({len(sec_lines)} lines)")

# Also find all assignments to ConsolidatedFSW[...] in Cell 61
assigned_cols = []
for i, line in enumerate(lines):
    m = re.search(r"ConsolidatedFSW\[['\"]([^'\"]+)['\"]\]\s*=", line)
    if m:
        assigned_cols.append((i + 1, m.group(1), line.strip()))

print(f"\nTotal columns assigned in Cell 61: {len(assigned_cols)}")
for lno, col, code in assigned_cols:
    print(f"L{lno:03d}: {col}")
