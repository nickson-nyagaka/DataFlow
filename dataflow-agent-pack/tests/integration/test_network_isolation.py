"""Integration test verifying zero outbound network calls during full pipeline execution.

Implements Phase 7 Exit Criterion & Decision D-047:
- Intercepts all socket connection attempts at the OS socket level.
- Verifies that running ingestion, cleaning, DQA, analytics, and reporting package generation
  makes ZERO outbound network calls.
"""

from __future__ import annotations

import io
import socket
from pathlib import Path
from typing import Any

import openpyxl
import pytest

from core.runner import run_full_pipeline
from tests.synthetic.generator import generate_synthetic_data


@pytest.fixture
def network_guard(monkeypatch):
    """Intercepts socket.socket.connect and tracks all connection attempts."""
    outbound_attempts: list[tuple[Any, ...]] = []
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else address
        # Allow localhost / loopback only
        if host in ("127.0.0.1", "localhost", "::1"):
            return real_connect(self, address)
        outbound_attempts.append(address)
        raise ConnectionRefusedError(
            f"DATAFLOW PRIVACY BREACH: Outbound network connection blocked to {address}"
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    return outbound_attempts


def test_zero_outbound_network_connections_during_full_pipeline_run(network_guard, tmp_path: Path):
    """Executes a complete pipeline run and verifies zero outbound connections."""
    # 1. Generate compliant synthetic cohort data
    fsw_reg, fsw_kp, _ = generate_synthetic_data("FSW", 100, seed=42)

    # Save to in-memory Excel workbook
    wb = openpyxl.Workbook()
    ws_reg = wb.active
    ws_reg.title = "Register"
    ws_reg.append(["FSW Cohort Register"])
    ws_reg.append([])
    ws_reg.append(list(fsw_reg.columns))
    for row in fsw_reg.itertuples(index=False):
        ws_reg.append(list(row))

    ws_kp = wb.create_sheet("KPLHIV")
    ws_kp.append(["KPLHIV Register"])
    ws_kp.append([])
    ws_kp.append(list(fsw_kp.columns))
    for row in fsw_kp.itertuples(index=False):
        ws_kp.append(list(row))

    buf = io.BytesIO()
    wb.save(buf)
    file_bytes = buf.getvalue()

    # 2. Run full pipeline under network guard
    result = run_full_pipeline(
        file_source=file_bytes,
        file_name="synthetic_fsw_test.xlsx",
        population="FSW",
        period_mode="SEM",
        force_rerun=True,
    )

    assert result is not None
    assert result.total_cohort > 0
    assert result.package_paths["master_workbook"].exists()
    assert result.package_paths["zip_package"].exists()

    # 3. Assert zero outbound network attempts
    assert len(network_guard) == 0, (
        f"Disallowed outbound network attempts detected: {network_guard}"
    )
