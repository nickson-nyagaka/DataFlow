#!/usr/bin/env python3
"""Check total_nsp_SEM in Cell 82."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, encoding="utf-8") as f:
    cells = json.load(f)

c82 = next(c for c in cells if c["index"] == 82)["source"]
lines = c82.splitlines()

for i, l in enumerate(lines):
    if "total_nsp" in l:
        print(f"{i + 1:3d}: {l}")
