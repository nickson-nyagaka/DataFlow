#!/usr/bin/env python3
"""Inspect headers definition in Cell 80."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)

c80 = next(c for c in cells if c["index"] == 80)["source"]
lines = c80.splitlines()

for i, l in enumerate(lines[:150]):
    if any(
        k in l for k in ["headers", "columns", "ws.append", "merge_cells", "blocks"]
    ):
        print(f"{i + 1:3d}: {l}")
