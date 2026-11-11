#!/usr/bin/env python3
"""Extract and inspect all cells from reference/OPTIMIZED_DATA_MGT.sanitized.ipynb."""

import json
from pathlib import Path

NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[2] / "reference" / "OPTIMIZED_DATA_MGT.sanitized.ipynb"
)


def main():
    with open(NOTEBOOK_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb.get("cells", [])
    print(f"Total cells: {len(cells)}")

    code_cells = []
    markdown_cells = []
    for idx, cell in enumerate(cells):
        ctype = cell.get("cell_type")
        source = "".join(cell.get("source", []))
        if ctype == "code":
            code_cells.append((idx, source))
        elif ctype == "markdown":
            markdown_cells.append((idx, source))

    print(f"Code cells: {len(code_cells)}")
    print(f"Markdown cells: {len(markdown_cells)}")

    # Save extracted dump for easy reference
    out_dir = Path(__file__).resolve().parent
    with open(out_dir / "cells_dump.json", "w", encoding="utf-8") as f:
        dump_data = [
            {
                "index": idx,
                "cell_type": cell.get("cell_type"),
                "source": "".join(cell.get("source", [])),
            }
            for idx, cell in enumerate(cells)
        ]
        json.dump(dump_data, f, indent=2)

    print(f"Saved cells dump to {out_dir / 'cells_dump.json'}")


if __name__ == "__main__":
    main()
