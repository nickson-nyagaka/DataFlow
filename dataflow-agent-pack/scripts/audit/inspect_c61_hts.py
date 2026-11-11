#!/usr/bin/env python3
"""Print lines 50 to 80 of Cell 61 (HTS_SEM)."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)

c61 = next(c for c in cells if c["index"] == 61)["source"]
lines = c61.splitlines()

for i in range(49, 80):
    print(f"{i + 1:3d}: {lines[i]}")
