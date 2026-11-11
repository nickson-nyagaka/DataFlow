#!/usr/bin/env python3
"""Inspect lines 250 to 350 of Cell 80."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)

c80 = next(c for c in cells if c["index"] == 80)["source"]
lines = c80.splitlines()

for i in range(249, min(350, len(lines))):
    print(f"{i + 1:3d}: {lines[i]}")
