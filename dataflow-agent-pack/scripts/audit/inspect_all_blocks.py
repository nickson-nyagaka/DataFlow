#!/usr/bin/env python3
"""Extract blocks from all four exporters."""

import ast
import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)


def get_cell(idx):
    for c in cells:
        if c["index"] == idx:
            return c["source"]
    return None


for idx in [75, 77, 80, 82]:
    src = get_cell(idx)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "blocks":
                    print(f"=== Cell {idx} Blocks ===")
                    for elt in node.value.elts:
                        # elt is tuple (grp, subs, cols)
                        grp = ast.literal_eval(elt.elts[0])
                        subs = ast.literal_eval(elt.elts[1])
                        cols = ast.literal_eval(elt.elts[2])
                        print(f"  Block: '{grp}' -> {list(zip(subs, cols))}")
