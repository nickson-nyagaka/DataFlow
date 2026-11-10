#!/usr/bin/env python3
"""Inspect cell 84 lines 60 to 120."""

import json
from pathlib import Path

DUMP_PATH = Path(__file__).resolve().parent / "cells_dump.json"

with open(DUMP_PATH, "r", encoding="utf-8") as f:
    cells = json.load(f)

for c in cells:
    if c["index"] == 84:
        for idx, line in enumerate(c["source"].splitlines()[59:120], start=60):
            print(f"{idx:3d}: {line}")
