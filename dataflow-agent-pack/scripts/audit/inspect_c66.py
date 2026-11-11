#!/usr/bin/env python3
"""Inspect Cell 66 in full."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)

c66 = next(c for c in cells if c["index"] == 66)["source"]
lines = c66.splitlines()
print(f"Cell 66 lines: {len(lines)}")
for i, line in enumerate(lines):
    print(f"{i + 1:3d}: {line}")
