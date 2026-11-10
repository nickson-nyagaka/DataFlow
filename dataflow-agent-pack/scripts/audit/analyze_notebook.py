#!/usr/bin/env python3
"""Programmatic analysis of the 89 cells (58 code cells)."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"


def main():
    with open(DUMP_PATH, "r", encoding="utf-8") as f:
        cells = json.load(f)

    print(f"Loaded {len(cells)} cells.")

    code_cells = [c for c in cells if c["cell_type"] == "code"]
    print(f"Code cells: {len(code_cells)}")

    for c in cells:
        idx = c["index"]
        ctype = c["cell_type"]
        src = c["source"].strip()
        first_line = src.splitlines()[0] if src else "(empty)"
        line_count = len(src.splitlines())
        if ctype == "markdown":
            print(f"[MD  Cell {idx:02d}] {first_line[:80]}")
        else:
            print(f"[CODE Cell {idx:02d}] ({line_count} lines) {first_line[:80]}")


if __name__ == "__main__":
    main()
