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


class ProcessingStageError(DataFlowError):
    """Structured exception identifying stage, operation, worksheet, column, cause, and action.

    Guarantees zero client PII exposure in error reporting and logging.
    """

    def __init__(
        self,
        stage: str,
        operation: str,
        problem: str,
        recommended_action: str,
        worksheet: str | None = None,
        column: str | None = None,
        row_num: int | None = None,
        likely_cause: str | None = None,
        technical_details: str | None = None,
    ) -> None:
        self.stage = stage
        self.operation = operation
        self.problem = problem
        self.recommended_action = recommended_action
        self.worksheet = worksheet
        self.column = column
        self.row_num = row_num
        self.likely_cause = likely_cause or "Input data does not conform to the expected template structure or format."
        self.technical_details = technical_details or ""

        # Construct clear base exception message
        msg_parts = [f"[{stage}] {operation}: {problem}"]
        if worksheet:
            msg_parts.append(f"(Worksheet: '{worksheet}')")
        if column:
            msg_parts.append(f"(Column: '{column}')")
        super().__init__(" ".join(msg_parts))

    def to_actionable_markdown(self) -> str:
        """Formats the error into a non-technical, user-friendly actionable message."""
        lines = [
            f"### ❌ {self.stage} Failed",
            f"**Operation:** {self.operation}",
        ]
        if self.worksheet:
            lines.append(f"**Worksheet:** `{self.worksheet}`")
        if self.column:
            lines.append(f"**Column:** `{self.column}`")
        if self.row_num is not None:
            lines.append(f"**Affected Row:** `Row {self.row_num}` *(approximate Excel row)*")

        lines.extend([
            "",
            f"**Problem:** {self.problem}",
            "",
            f"**Likely Cause:** {self.likely_cause}",
            "",
            "**How to fix this:**",
            self.recommended_action,
        ])
        return "\n".join(lines)
