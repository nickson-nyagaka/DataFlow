"""Unit tests for diagnostic bundle generation and privacy scrubbing."""

import json
import zipfile
from pathlib import Path

from core.diagnostics import (
    build_diagnostic_bundle,
    collect_config_hashes,
    collect_system_environment,
    scrub_sensitive_text,
)


def test_scrub_sensitive_text():
    raw = (
        "Encountered error for client FSW-123456 and peer educator PE-04 "
        "with NUPI 12345-67890 and CCC 1234567890. Email: test@example.com."
    )
    scrubbed = scrub_sensitive_text(raw)
    assert "FSW-123456" not in scrubbed
    assert "PE-04" not in scrubbed
    assert "12345-67890" not in scrubbed
    assert "1234567890" not in scrubbed
    assert "test@example.com" not in scrubbed
    assert "[REDACTED_UIC]" in scrubbed
    assert "[REDACTED_NUPI]" in scrubbed
    assert "[REDACTED_CCC]" in scrubbed


def test_collect_system_environment():
    env = collect_system_environment()
    assert "platform" in env
    assert "python_version" in env
    assert "cpu_count" in env
    assert env["cpu_count"] >= 1


def test_collect_config_hashes():
    hashes = collect_config_hashes()
    assert len(hashes) > 0
    # Every hash is 64 hex characters (SHA-256)
    for path, h in hashes.items():
        assert len(h) == 64
        assert path.endswith(".yaml")


def test_build_diagnostic_bundle(tmp_path: Path):
    out_dir = tmp_path / "diagnostics"
    bundle = build_diagnostic_bundle(
        error_traceback="Traceback: Crash on row with UIC FSW-99999",
        extra_context={"population": "FSW", "client": "MSM-88888"},
        output_dir=out_dir,
    )

    assert bundle.exists()
    assert bundle.name.startswith("dataflow_support_bundle_")
    assert bundle.name.endswith(".zip")

    # Inspect zip contents
    with zipfile.ZipFile(bundle, "r") as zf:
        names = zf.namelist()
        assert "system_environment.json" in names
        assert "config_hashes.json" in names
        assert "error_traceback.txt" in names
        assert "extra_context.json" in names

        tb_content = zf.read("error_traceback.txt").decode("utf-8")
        assert "FSW-99999" not in tb_content
        assert "[REDACTED_UIC]" in tb_content

        ctx_content = json.loads(zf.read("extra_context.json").decode("utf-8"))
        assert ctx_content["client"] == "[REDACTED_UIC]"
