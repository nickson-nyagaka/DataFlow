"""Privacy-safe identifier-scrubbing logger for DATAFLOW.

Guarantees that sensitive Key Population identifiers (UICs, CCC numbers, names, DOBs)
never appear in application log streams, tracebacks, or formatted outputs.
"""

from __future__ import annotations

import logging
import re
import sys
import traceback
from typing import Any

# Regex patterns matching sensitive identifiers:
# 1. Standard UIC patterns (e.g. NRR/FSW/0012, MOM-2024-999, FSW123456, UIC_999999)
UIC_PATTERN = re.compile(
    r"\b(?:[A-Z]{2,4}[/-][A-Z0-9]{2,6}[/-][0-9]{3,6}|[A-Z]{2,5}[-_]?[0-9]{4,8}|UIC[-_]?[A-Z0-9]{4,12})\b",
    re.IGNORECASE,
)

# 2. CCC / NUPI numbers (10-digit identifiers or hyphenated facility-client IDs)
CCC_PATTERN = re.compile(r"\b(?:\d{5}[-_]?\d{5}|\d{10})\b")

# 3. Explicit planted test identifiers or phone numbers (e.g. +2547..., 0712...)
PHONE_PATTERN = re.compile(r"\b(?:\+?254|0)[17]\d{8}\b")

# 4. Explicit UIC label followed by string: uic="...", uic: "..."
EXPLICIT_UIC_LABEL = re.compile(
    r"""(?i)(?:uic|ccc_number|nupi)\s*[:=]\s*['"]?([A-Za-z0-9/_-]+)['"]?"""
)


class IdentifierScrubbingFilter(logging.Filter):
    """Logging filter that scrubs personal identifiers from log messages and exception text."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.scrub_text(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._scrub_obj(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._scrub_obj(a) for a in record.args)

        if record.exc_info:
            raw_tb = "".join(traceback.format_exception(*record.exc_info))
            record.exc_text = self.scrub_text(raw_tb)
            record.exc_info = None

        if record.exc_text:
            record.exc_text = self.scrub_text(record.exc_text)

        return True

    @classmethod
    def scrub_text(cls, text: str) -> str:
        if not isinstance(text, str):
            return text

        scrubbed = EXPLICIT_UIC_LABEL.sub(r"uic=[REDACTED_IDENTIFIER]", text)
        scrubbed = UIC_PATTERN.sub("[REDACTED_UIC]", scrubbed)
        scrubbed = CCC_PATTERN.sub("[REDACTED_CCC]", scrubbed)
        scrubbed = PHONE_PATTERN.sub("[REDACTED_PHONE]", scrubbed)
        return scrubbed

    @classmethod
    def _scrub_obj(cls, obj: Any) -> Any:
        if isinstance(obj, str):
            return cls.scrub_text(obj)
        return obj


class IdentifierScrubbingFormatter(logging.Formatter):
    """Formatter that guarantees complete scrubbing on final rendered log line."""

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        return IdentifierScrubbingFilter.scrub_text(s)


def get_logger(name: str = "dataflow", level: int = logging.INFO) -> logging.Logger:
    """Returns a configured logger with the IdentifierScrubbingFilter applied."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if get_logger is called repeatedly
    if not any(isinstance(f, IdentifierScrubbingFilter) for f in logger.filters):
        logger.addFilter(IdentifierScrubbingFilter())

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = IdentifierScrubbingFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(IdentifierScrubbingFilter())
        logger.addHandler(handler)

    return logger
