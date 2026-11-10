#!/usr/bin/env python3
"""Phase-gate checker.

Usage:
    python scripts/gate_check.py          -> prints the one phase that may be worked on
    python scripts/gate_check.py 3        -> exit 0 only if phase 3 is the allowed phase

The agent may only work on the lowest-numbered phase that is not APPROVED.
Approvals must be contiguous: phase N cannot be APPROVED while an earlier phase is not.
"""
from __future__ import annotations

import pathlib
import re
import sys

GATE_FILE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "gates" / "PHASE_APPROVALS.md"
LINE = re.compile(r"^PHASE\s+(\d+)\s*\|\s*STATUS:\s*(PENDING|APPROVED|REJECTED)\b", re.IGNORECASE)
EXPECTED = list(range(8))


def read_statuses(path: pathlib.Path) -> dict[int, str]:
    if not path.exists():
        raise SystemExit(f"GATE ERROR: {path} not found. Stop and tell the Owner.")
    found: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw.strip())
        if m:
            n = int(m.group(1))
            if n in found:
                raise SystemExit(f"GATE ERROR: phase {n} appears more than once.")
            found[n] = m.group(2).upper()
    missing = [n for n in EXPECTED if n not in found]
    if missing:
        raise SystemExit(f"GATE ERROR: missing phase line(s): {missing}")
    return found


def current_phase(statuses: dict[int, str]) -> int | None:
    seen_unapproved = False
    for n in EXPECTED:
        if statuses[n] == "APPROVED":
            if seen_unapproved:
                raise SystemExit(
                    f"GATE ERROR: phase {n} is APPROVED but an earlier phase is not. "
                    "Stop and tell the Owner; do not work."
                )
        else:
            seen_unapproved = True
    for n in EXPECTED:
        if statuses[n] != "APPROVED":
            return n
    return None


def main(argv: list[str]) -> int:
    statuses = read_statuses(GATE_FILE)
    cur = current_phase(statuses)
    if cur is None:
        print("ALL PHASES APPROVED. No further phase work is allowed without new instructions from the Owner.")
        return 0 if len(argv) < 2 else 1
    rework = " (REJECTED: rework only the defects in docs/gates/REJECTIONS.md)" if statuses[cur] == "REJECTED" else ""
    if len(argv) < 2:
        print(f"ALLOWED PHASE: {cur}{rework}")
        print("You may work on this phase and no other. Do not edit docs/gates/PHASE_APPROVALS.md.")
        return 0
    wanted = int(argv[1])
    if wanted == cur:
        print(f"OK: phase {wanted} is the allowed phase{rework}.")
        return 0
    print(f"BLOCKED: phase {wanted} is not allowed. The only allowed phase is {cur}.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
