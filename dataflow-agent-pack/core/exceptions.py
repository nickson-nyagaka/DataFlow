"""Domain exception hierarchy for DATAFLOW."""

from __future__ import annotations


class DataFlowError(Exception):
    """Base exception for all DATAFLOW errors."""


class ConfigValidationError(DataFlowError):
    """Raised when configuration YAML fails schema validation."""

    def __init__(self, message: str, file: str | None = None, key: str | None = None) -> None:
        self.file = file
        self.key = key
        parts = []
        if file:
            parts.append(f"file '{file}'")
        if key:
            parts.append(f"key '{key}'")
        prefix = f"Config error in {', '.join(parts)}: " if parts else "Config error: "
        super().__init__(f"{prefix}{message}")


class IngestionError(DataFlowError):
    """Raised during workbook reading, format detection, or sheet loading."""


class SchemaMismatchError(DataFlowError):
    """Raised when required columns cannot be resolved or aliases are ambiguous."""


class CleaningError(DataFlowError):
    """Raised when data cleaning or type conversion fails."""


class DQAError(DataFlowError):
    """Raised when critical DQA rules fail and block execution."""


class PeriodMappingError(DataFlowError):
    """Raised when source columns cannot be unambiguously mapped to reporting periods."""


class AnalyticalError(DataFlowError):
    """Raised during indicator calculation or summary aggregation."""


class ExportError(DataFlowError):
    """Raised during Excel workbook generation or formatting."""
