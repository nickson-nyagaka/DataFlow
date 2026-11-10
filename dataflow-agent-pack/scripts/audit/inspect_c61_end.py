#!/usr/bin/env python3
"""Print lines 180 to 247 of Cell 61."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)

c61 = next(c for c in cells if c["index"] == 61)["source"]
lines = c61.splitlines()

for i in range(179, len(lines)):
    print(f"{i + 1:3d}: {lines[i]}")
