#!/usr/bin/env python3
"""Extract every output column produced by any .agg(...) or export block."""

import json
import re
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)


def get_cell(idx):
    for c in cells:
        if c["index"] == idx:
            return c["source"]
    return None


# Cells with .agg() or exports
# Cell 54: summary_KPLHIV
# Cell 66: summary_FSW
# Cell 75: build_summary_fsw (Q1 non-PWID)
# Cell 77: build_summary_fsw (Q1 PWID)
# Cell 80: build_summary_fsw (Full non-PWID)
# Cell 82: build_summary_fsw (Full PWID)
# Cell 84: age/sex pivot

all_columns = {}

for idx in [54, 66, 75, 77, 80, 82, 84]:
    src = get_cell(idx)
    # Find .agg(...) definitions
    agg_blocks = re.findall(r"\.agg\s*\((.*?)\)", src, re.DOTALL)
    for block in agg_blocks:
        pairs = re.findall(
            r'([a-zA-Z0-9_]+)\s*=\s*\(([\'"][^\'"]+[\'"]\s*,\s*[\'"][^\'"]+[\'"])\)',
            block,
        )
        if pairs:
            for col_name, expr in pairs:
                all_columns[col_name] = {"source_cell": idx, "agg_expr": expr}
        else:
            # maybe dict syntax: .agg({'col': 'sum', ...})
            dict_pairs = re.findall(r'[\'"]([^\'"]+)[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', block)
            for col_name, func in dict_pairs:
                all_columns[col_name] = {"source_cell": idx, "agg_expr": func}

# Also find headers from exporters
for idx in [75, 77, 80, 82]:
    src = get_cell(idx)
    # find headers list of tuples
    # (col_name, subheader, width, ...)
    # Look for ("...", "...", ...)
    matches = re.findall(r'\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']', src)
    # print headers found
    print(f"Exporter Cell {idx} header matches count: {len(matches)}")

print("\nAggregated Columns Found across all cells:")
for k, v in sorted(all_columns.items()):
    print(f"- {k} (from cell {v['source_cell']}): {v['agg_expr']}")
