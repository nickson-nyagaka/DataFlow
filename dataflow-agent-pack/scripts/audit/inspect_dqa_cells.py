#!/usr/bin/env python3
"""Inspect DQA and Active check cells: 34, 36, 40, 42, 45, 48, 50."""

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


for idx in [24, 26, 28, 30, 34, 36, 40, 42, 45, 48, 50]:
    c = get_cell(idx)
    print("=" * 60)
    print(f"Cell {idx}")
    print("=" * 60)
    print(c[:800] if c else "None")
    print()
