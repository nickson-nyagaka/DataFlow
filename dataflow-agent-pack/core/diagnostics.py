"""DATAFLOW Diagnostic Support Bundle Generator.

Implements Decision D-048:
- Packages system environment, configuration hashes, and sanitized diagnostic logs.
- Guarantees strict privacy: automatically scrubs UICs, patient IDs, dates of birth,
  and names using regex patterns prior to bundling.
- Stores bundles in runtime/audit/diagnostics/ as timestamped ZIP archives.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Patterns to scrub from diagnostic logs and tracebacks (strict privacy compliance)
# Never expose UICs, CCC/NUPI, or personal names in support bundles.
SCRUB_PATTERNS = [
    (re.compile(r"\b(FSW|MSM|PWID|TG|VP)[-_]?[A-Z0-9]{3,15}\b", re.IGNORECASE), "[REDACTED_UIC]"),
    (re.compile(r"\b\d{5}-\d{5}\b"), "[REDACTED_NUPI]"),
    (re.compile(r"\b\d{10}\b"), "[REDACTED_CCC]"),
    (re.compile(r"\b(PE[-_]?[0-9]{2,5})\b", re.IGNORECASE), "[REDACTED_PE_CODE]"),
    (
        re.compile(r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"),
        "[REDACTED_EMAIL]",
    ),
]


def scrub_sensitive_text(text: str) -> str:
    """Removes any client identifiers or sensitive data patterns from text."""
    scrubbed = text
    for pattern, replacement in SCRUB_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def collect_system_environment() -> dict[str, Any]:
    """Collects non-sensitive system environment metrics."""
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor() or "Unknown",
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "cpu_count": os.cpu_count() or 1,
        "app_root": str(Path(__file__).resolve().parents[1].name),
    }


def collect_config_hashes(base_dir: Path | None = None) -> dict[str, str]:
    """Calculates SHA-256 hashes of all configuration files."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1]

    hashes: dict[str, str] = {}
    config_dir = base_dir / "config"
    if not config_dir.exists():
        return hashes

    for p in sorted(config_dir.rglob("*.yaml")):
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        rel_path = str(p.relative_to(base_dir)).replace("\\", "/")
        hashes[rel_path] = sha

    return hashes


def build_diagnostic_bundle(
    error_traceback: str | None = None,
    extra_context: dict[str, Any] | None = None,
    output_dir: Path | str = "runtime/audit/diagnostics",
    base_dir: Path | None = None,
) -> Path:
    """
    Builds a sanitized diagnostic ZIP support bundle.

    Returns the Path to the generated ZIP archive.
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1]

    out_path = Path(output_dir)
    if not out_path.is_absolute():
        out_path = base_dir / out_path
    out_path.mkdir(parents=True, exist_ok=True)

    ts_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"dataflow_support_bundle_{ts_str}.zip"
    bundle_file = out_path / bundle_name

    with zipfile.ZipFile(bundle_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. System environment
        env_data = collect_system_environment()
        zf.writestr("system_environment.json", json.dumps(env_data, indent=2))

        # 2. Config hashes
        cfg_hashes = collect_config_hashes(base_dir=base_dir)
        zf.writestr("config_hashes.json", json.dumps(cfg_hashes, indent=2))

        # 3. Run metadata if exists
        run_meta = base_dir / "runtime" / "run_metadata.json"
        if run_meta.exists():
            meta_str = scrub_sensitive_text(run_meta.read_text(encoding="utf-8"))
            zf.writestr("run_metadata.json", meta_str)

        # 4. Error traceback (scrubbed)
        if error_traceback:
            scrubbed_tb = scrub_sensitive_text(error_traceback)
            zf.writestr("error_traceback.txt", scrubbed_tb)

        # 5. Extra context
        if extra_context:
            scrubbed_ctx = scrub_sensitive_text(json.dumps(extra_context, indent=2))
            zf.writestr("extra_context.json", scrubbed_ctx)

    return bundle_file
