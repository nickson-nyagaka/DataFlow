"""Audit trail and reconciliation tracking for DATAFLOW ingestion and cleaning."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from core.exceptions import IngestionError


@dataclass
class SheetAudit:
    """Audit metrics for a single sheet (e.g. Register or KPLHIV)."""

    sheet_name: str
    rows_in: int = 0
    rows_out: int = 0
    dropped_empty_rows: int = 0
    dropped_records: dict[str, int] = field(default_factory=dict)
    detected_skiprows: int = 0
    input_sha256: str = ""
    cleaned_sha256: str = ""

    def total_dropped(self) -> int:
        return self.dropped_empty_rows + sum(self.dropped_records.values())

    def reconcile(self) -> bool:
        """Verifies that rows_in == rows_out + total_dropped."""
        expected = self.rows_out + self.total_dropped()
        if self.rows_in != expected:
            raise IngestionError(
                f"Audit trail reconciliation failed for sheet '{self.sheet_name}': "
                f"rows_in ({self.rows_in}) != rows_out ({self.rows_out}) + dropped ({self.total_dropped()})"
            )
        return True


@dataclass
class WorkbookAudit:
    """Full audit record for an ingested workbook."""

    file_path: str
    population: str
    file_sha256: str = ""
    sheets: dict[str, SheetAudit] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_sheet_audit(self, sheet_audit: SheetAudit) -> None:
        sheet_audit.reconcile()
        self.sheets[sheet_audit.sheet_name] = sheet_audit

    def reconcile_all(self) -> bool:
        for audit in self.sheets.values():
            audit.reconcile()
        return True

    @staticmethod
    def compute_frame_hash(df: pd.DataFrame) -> str:
        """Computes a deterministic SHA-256 hash of a DataFrame's contents."""
        # Convert DataFrame to a canonical byte representation
        data_bytes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
        return hashlib.sha256(data_bytes).hexdigest()
