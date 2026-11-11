#!/usr/bin/env python3
"""Comprehensive programmatic audit of all 89 cells."""

import json
import re
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)

print(f"Total cells: {len(cells)}")

results = []
for c in cells:
    idx = c["index"]
    ctype = c["cell_type"]
    src = c["source"]
    lines = src.splitlines()

    # Simple regex analysis of python code
    inputs = set()
    outputs = set()
    agg_cols = []

    if ctype == "code":
        # Find variable assignments: var = ...
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("#"):
                continue
            # match var = ...
            m_assign = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=", line_str)
            if m_assign:
                outputs.add(m_assign.group(1))
            # match df['col'] = ...
            m_col_assign = re.match(
                r"^([a-zA-Z_][a-zA-Z0-9_]*)\[['\"]([^'\"]+)['\"]\]\s*=", line_str
            )
            if m_col_assign:
                outputs.add(f"{m_col_assign.group(1)}['{m_col_assign.group(2)}']")

            # match .agg(...)
            if ".agg(" in line_str:
                agg_cols.append(line_str)

    results.append({"index": idx, "type": ctype, "lines": len(lines), "source": src})

print("Audited all cells.")
