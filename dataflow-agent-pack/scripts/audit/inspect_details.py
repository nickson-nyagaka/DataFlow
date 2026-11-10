#!/usr/bin/env python3
"""Deeper inspection of cell 84, cell 61, and exporters 75, 77, 80, 82."""

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


c84 = get_cell(84)
# Let's inspect age/sex parts of c84
print("--- Cell 84 snippet (age/sex/fillna) ---")
lines84 = c84.splitlines()
for i, l in enumerate(lines84[:60]):
    print(f"{i + 1:3d}: {l}")

print("\n--- Cell 61 start (first 50 lines) ---")
c61 = get_cell(61)
lines61 = c61.splitlines()
for i, l in enumerate(lines61[:50]):
    print(f"{i + 1:3d}: {l}")

print("\n--- Exporter comparison (75, 77, 80, 82) ---")
c75 = get_cell(75)
c77 = get_cell(77)
c80 = get_cell(80)
c82 = get_cell(82)

print(f"Cell 75 lines: {len(c75.splitlines())}")
print(f"Cell 77 lines: {len(c77.splitlines())}")
print(f"Cell 80 lines: {len(c80.splitlines())}")
print(f"Cell 82 lines: {len(c82.splitlines())}")
