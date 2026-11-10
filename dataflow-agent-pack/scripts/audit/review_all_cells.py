#!/usr/bin/env python3
"""Detailed review of all 89 cells."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)

for c in cells:
    idx = c["index"]
    ctype = c["cell_type"]
    src = c["source"].strip()
    lines = src.splitlines()
    print(f"=== Cell {idx:02d} ({ctype}, {len(lines)} lines) ===")
    if len(lines) > 0:
        for l in lines[:5]:
            print(f"  {l}")
        if len(lines) > 5:
            print(f"  ... (+{len(lines) - 5} more lines)")
    else:
        print("  (empty)")
