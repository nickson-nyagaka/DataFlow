#!/usr/bin/env python3
"""Create a copy of a notebook with ALL outputs removed.

Why: saved outputs can contain client-level rows (UICs, CCC numbers). Run this BEFORE the
notebook goes anywhere near an AI agent or a repository.

Usage:
    python scripts/sanitize_notebook.py <original.ipynb> <sanitized.ipynb> [--force]

The original is never modified. Prints counts only, never cell contents.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ABS_PATH = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\")


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    force = "--force" in argv
    if len(args) != 2:
        print(__doc__)
        return 2
    src, dst = pathlib.Path(args[0]), pathlib.Path(args[1])
    if src.resolve() == dst.resolve():
        print("Refusing: destination equals source.")
        return 2
    if dst.exists() and not force:
        print(f"Refusing: {dst} exists (use --force).")
        return 2
    nb = json.loads(src.read_text(encoding="utf-8"))
    cleared = removed_bytes = path_cells = 0
    for idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            if cell.get("outputs"):
                removed_bytes += len(json.dumps(cell["outputs"]))
                cleared += 1
            cell["outputs"] = []
            cell["execution_count"] = None
            if ABS_PATH.search("".join(cell.get("source", []))):
                path_cells += 1
        cell.get("metadata", {}).pop("scrolled", None)
    nb.get("metadata", {}).pop("widgets", None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"cells: {len(nb.get('cells', []))}")
    print(f"cells with outputs cleared: {cleared} ({removed_bytes:,} bytes of output removed)")
    print(f"code cells containing absolute machine paths (left as-is, to be audited): {path_cells}")
    print(f"written: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
