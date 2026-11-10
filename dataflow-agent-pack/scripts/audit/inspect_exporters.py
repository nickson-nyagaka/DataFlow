#!/usr/bin/env python3
"""Analyze the four exporters: cells 75, 77, 80, 82."""

import json
import re
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)


def get_cell(idx):
    for c in cells:
        if c["index"] == idx:
            return c["source"]
    return None


c75 = get_cell(75)
c77 = get_cell(77)
c80 = get_cell(80)
c82 = get_cell(82)

exporters = [
    (75, "Q1 non-PWID (KP_Summary)", c75),
    (77, "Q1 PWID (PWID_Summary)", c77),
    (80, "Q1/Q2/SEM non-PWID (Summary)", c80),
    (82, "Q1/Q2/SEM PWID (PWID_Summary)", c82),
]

for idx, label, code in exporters:
    lines = code.splitlines()
    print(f"=== Cell {idx}: {label} ({len(lines)} lines) ===")

    # Find sheet name
    sheet_matches = re.findall(
        r'ws\s*=\s*wb\.create_sheet\s*\(\s*title\s*=\s*["\']([^"\']+)["\']', code
    )
    if not sheet_matches:
        sheet_matches = re.findall(r'title\s*=\s*["\']([^"\']+)["\']', code)
    print(f"Sheet titles: {sheet_matches}")

    # Find header blocks / columns
    # Find headers definition
    headers_match = re.search(r"headers\s*=\s*(\[.*?\]\s*\n\s*\])", code, re.DOTALL)
    if not headers_match:
        # maybe headers = [ ... ]
        pass

    # Find columns written to excel
    cols_written = re.findall(r'row\.get\([\'"]([^\'"]+)[\'"]', code)
    if not cols_written:
        cols_written = re.findall(r'\[[\'"]([^\'"]+)[\'"]\]', code)
    print(f"Sample columns referenced ({len(cols_written)} total)")
