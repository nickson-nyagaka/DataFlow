#!/usr/bin/env python3
"""Parse all .agg() and exporter columns using AST."""

import ast
import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)

agg_columns = {}
exporter_columns = {}

for c in cells:
    idx = c["index"]
    src = c["source"]
    if c["cell_type"] != "code" or not src.strip():
        continue

    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        # Some cells might have IPython magic or syntax error
        # Clean lines starting with % or !
        cleaned = "\n".join(l for l in src.splitlines() if not l.strip().startswith(("%", "!")))
        try:
            tree = ast.parse(cleaned)
        except (SyntaxError, ValueError) as e2:
            print(f"Skipping cell {idx} AST parse error: {e2}")
            continue

    for node in ast.walk(tree):
        # Look for .agg(...) calls
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "agg"
        ):
            # Check keywords
            for kw in node.keywords:
                agg_name = kw.arg
                # value is tuple ('col', 'func')
                val_repr = ast.unparse(kw.value)
                agg_columns[agg_name] = {"cell": idx, "expr": val_repr}
        # Look for headers = [...] in exporters
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "headers"
                    and isinstance(node.value, ast.List)
                ):
                    headers_list = []
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Tuple):
                            vals = [ast.unparse(e) for e in elt.elts]
                            headers_list.append(vals)
                    exporter_columns[idx] = headers_list

print(f"Total .agg keywords found: {len(agg_columns)}")
for k, v in sorted(agg_columns.items()):
    print(f"  {k} (Cell {v['cell']}): {v['expr']}")

print(f"\nExporters with headers list: {list(exporter_columns.keys())}")
for idx, hdrs in exporter_columns.items():
    print(f"\nCell {idx} headers count: {len(hdrs)}")
    for h in hdrs:
        print(f"    {h}")
