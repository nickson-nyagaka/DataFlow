#!/usr/bin/env python3
"""Gate checker (v2: phases first, then work packages).

Usage:
    python scripts/gate_check.py          -> prints what may be worked on
    python scripts/gate_check.py S3       -> exit 0 only if S3 is the allowed work package

Mode 1: while any build phase (0-7) is not APPROVED, behaves exactly as v1.
Mode 2: once all phases are APPROVED, the allowed work is the single WP in
        docs/gates/WORK_PACKAGES.md whose status is ACTIVE (or REJECTED = rework).
Exit codes: 0 ok / none active, 1 blocked, 2 gate file error, 3 baseline tag missing.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PHASE_FILE = ROOT / "docs" / "gates" / "PHASE_APPROVALS.md"
GATE_FILE = PHASE_FILE
WP_FILE = ROOT / "docs" / "gates" / "WORK_PACKAGES.md"
PHASE_LINE = re.compile(r"^PHASE\s+(\d+)\s*\|\s*STATUS:\s*(PENDING|APPROVED|REJECTED)\b", re.I)
WP_LINE = re.compile(
    r"^WP\s+([A-Za-z0-9\-]+)\s*\|\s*STATUS:\s*(QUEUED|ACTIVE|APPROVED|REJECTED)\s*\|\s*"
    r"type:\s*(STRESS|FIX|ENHANCE)\s*\|\s*golden_update:\s*(allowed|no)\s*(?:\|\s*title:\s*(.*))?$",
    re.I,
)
BASELINE = re.compile(r"^baseline_tag:\s*(\S+)\s*$", re.I | re.M)
PHASES = list(range(8))


def die(msg: str, code: int = 2) -> None:
    print(msg)
    raise SystemExit(msg)


def read_statuses(path: Path | None = None) -> dict[int, str]:
    target = path if path is not None else GATE_FILE
    if not target.exists():
        die(f"GATE ERROR: {target} not found. Stop and tell the Owner.")
    found: dict[int, str] = {}
    for raw in target.read_text(encoding="utf-8").splitlines():
        m = PHASE_LINE.match(raw.strip())
        if m:
            n = int(m.group(1))
            if n in found:
                die(f"GATE ERROR: phase {n} appears more than once.")
            found[n] = m.group(2).upper()
    missing = [n for n in PHASES if n not in found]
    if missing:
        die(f"GATE ERROR: missing phase line(s): {missing}")
    return found


def read_phases() -> dict[int, str]:
    return read_statuses(GATE_FILE)


def current_phase(st: dict[int, str]) -> int | None:
    seen = False
    for n in PHASES:
        if st[n] == "APPROVED":
            if seen:
                die(f"GATE ERROR: phase {n} is APPROVED but an earlier phase is not. Stop; do not work.")
        else:
            seen = True
    for n in PHASES:
        if st[n] != "APPROVED":
            return n
    return None


def read_wps() -> tuple[str | None, list[dict[str, str]]]:
    if not WP_FILE.exists():
        die(f"GATE ERROR: {WP_FILE} not found. Stop and tell the Owner.")
    text = WP_FILE.read_text(encoding="utf-8")
    m = BASELINE.search(text)
    baseline = m.group(1) if m else None
    wps: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for raw in text.splitlines():
        w = WP_LINE.match(raw.strip())
        if w:
            wid = w.group(1).upper()
            if wid in seen_ids:
                die(f"GATE ERROR: work package {wid} appears more than once.")
            seen_ids.add(wid)
            wps.append({"id": wid, "status": w.group(2).upper(), "type": w.group(3).upper(),
                        "golden": w.group(4).lower(), "title": (w.group(5) or "").strip()})
    if not wps:
        die("GATE ERROR: no work-package lines found.")
    return baseline, wps


def check_baseline(tag: str | None) -> None:
    if not tag:
        die("GATE ERROR: baseline_tag is not set in WORK_PACKAGES.md.")
    if shutil.which("git") is None:
        print("WARNING: git not found; baseline tag not verified.")
        return
    res = subprocess.run(["git", "tag", "-l", tag], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print("WARNING: not a git repository; baseline tag not verified.")
        return
    if tag not in res.stdout.split():
        die(f"BASELINE TAG MISSING: '{tag}' does not exist. Stop and tell the Owner.", 3)


def main(argv: list[str]) -> int:
    phases = read_phases()
    cur = current_phase(phases)
    if cur is not None:  # Mode 1: v1 behaviour
        rework = " (REJECTED: rework only the defects in docs/gates/REJECTIONS.md)" if phases[cur] == "REJECTED" else ""
        if len(argv) < 2:
            print(f"ALLOWED PHASE: {cur}{rework}")
            print("Work on this phase and no other. Do not edit docs/gates/PHASE_APPROVALS.md.")
            return 0
        if argv[1].isdigit() and int(argv[1]) == cur:
            print(f"OK: phase {cur} is the allowed phase{rework}.")
            return 0
        print(f"BLOCKED: phase {argv[1]} is not allowed. The only allowed phase is {cur}.")
        return 1

    baseline, wps = read_wps()  # Mode 2
    active = [w for w in wps if w["status"] in ("ACTIVE", "REJECTED")]
    if len(active) > 1:
        die("GATE ERROR: more than one work package is ACTIVE/REJECTED: "
            + ", ".join(w["id"] for w in active) + ". Stop; do not work.")
    check_baseline(baseline)
    if not active:
        print("NO ACTIVE WORK PACKAGE. All build phases are approved; no work is allowed until the Owner activates one.")
        return 0 if len(argv) < 2 else 1
    w = active[0]
    rework = " (REJECTED: rework only the defects in docs/gates/REJECTIONS.md)" if w["status"] == "REJECTED" else ""
    if len(argv) < 2:
        print(f"ALLOWED WORK PACKAGE: {w['id']} (type: {w['type']}, golden_update: {w['golden']}) - {w['title']}{rework}")
        print("Work on this package and no other. Do not edit docs/gates/WORK_PACKAGES.md.")
        return 0
    if argv[1].upper() == w["id"]:
        print(f"OK: {w['id']} is the allowed work package{rework}.")
        return 0
    print(f"BLOCKED: only work package {w['id']} is allowed.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
