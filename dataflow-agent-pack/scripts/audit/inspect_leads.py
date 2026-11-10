#!/usr/bin/env python3
"""Inspect specific cells for leads L-01 to L-17."""

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


def print_section(title, content):
    print("=" * 60)
    print(title)
    print("=" * 60)
    print(content)
    print()


# Check Cell 46 (L-01)
print_section("Cell 46 (L-01)", get_cell(46))

# Check Cell 38 (L-02)
print_section("Cell 38 (L-02)", get_cell(38))

# Check Cell 17 (L-03)
print_section("Cell 17 (L-03)", get_cell(17))

# Check Cleaning cells: 04, 06, 08, 10, 12, 14 (L-04, L-14)
print_section("Cell 04 (L-04, L-14)", get_cell(4))
print_section("Cell 14 (L-04, L-14)", get_cell(14))

# Check Cell 57 and 84 (L-05, L-06)
print_section("Cell 57 (L-05)", get_cell(57))
# Check cell 84 age/sex lines
c84 = get_cell(84)
if c84:
    lines84 = [
        line
        for line in c84.splitlines()
        if any(k in line for k in ["fillna", "age", "sex"])
    ]
    print_section("Cell 84 age/sex snippets (L-05, L-06)", "\n".join(lines84[:20]))

# Check Cell 54 (L-08)
print_section("Cell 54 (L-08)", get_cell(54))

# Check Cell 61 snippets (L-07, L-10, L-15, L-17)
c61 = get_cell(61)
print(f"Cell 61 total lines: {len(c61.splitlines())}")

# Check Cell 52 (L-16)
print_section("Cell 52 CCC check (L-16)", get_cell(52)[:1500])

# Check Cell 69 (L-11)
print_section("Cell 69 OLD/NEW cohort (L-11)", get_cell(69)[:1500])
