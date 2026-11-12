"""Pre-Processing Template Concordance Validator for DATAFLOW.

Audits uploaded workbooks against the official Kenya KP Cohort Register template (reference/KP_TEMPLATE.xlsx)
BEFORE analytical calculations, DQA, or reporting packages are executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.ingestion import get_workbook_sheet_names, normalize_token
from core.template_schema import is_kp_template_register


def extract_sheet_headers(p: Path, sheet_name: str, expected_skiprows: int = 2) -> list[str]:
    """Safely reads the raw header row from any supported format (.xlsx, .xlsm, .xlsb, .xls, .csv)."""
    ext = p.suffix.lower()

    # 1. Try python_calamine (fast, native support for xlsb, xlsx, xlsm, xls)
    try:
        from python_calamine import CalamineWorkbook

        wb = CalamineWorkbook.from_path(str(p))
        matches = [s for s in wb.sheet_names if s.strip().lower() == sheet_name.strip().lower()]
        if matches:
            ws = wb.get_sheet_by_name(matches[0])
            for idx, row in enumerate(ws.iter_rows()):
                if idx == expected_skiprows:
                    headers = [str(cell or "").strip() for cell in row]
                    while headers and not headers[-1]:
                        headers.pop()
                    return headers
    except Exception:
        pass

    # 2. Try pyxlsb for .xlsb
    if ext == ".xlsb":
        try:
            import pyxlsb

            with pyxlsb.open_workbook(str(p)) as wb:
                matches = [s for s in wb.sheets if s.strip().lower() == sheet_name.strip().lower()]
                if matches:
                    with wb.get_sheet(matches[0]) as ws:
                        for idx, row in enumerate(ws.rows()):
                            if idx == expected_skiprows:
                                headers = [str(cell.v or "").strip() for cell in row]
                                while headers and not headers[-1]:
                                    headers.pop()
                                return headers
        except Exception:
            pass

    # 3. Try openpyxl for .xlsx, .xlsm
    if ext in [".xlsx", ".xlsm"]:
        try:
            import openpyxl

            wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
            matches = [s for s in wb.sheetnames if s.strip().lower() == sheet_name.strip().lower()]
            if matches:
                ws = wb[matches[0]]
                header_row_num = expected_skiprows + 1
                for row in ws.iter_rows(
                    min_row=header_row_num, max_row=header_row_num, values_only=True
                ):
                    headers = [str(cell or "").strip() for cell in row]
                    while headers and not headers[-1]:
                        headers.pop()
                    wb.close()
                    return headers
            wb.close()
        except Exception:
            pass

    # 4. Try csv for .csv
    if ext == ".csv":
        try:
            import csv

            with p.open("r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.reader(f)
                for idx, row in enumerate(reader):
                    if idx == expected_skiprows:
                        headers = [str(cell or "").strip() for cell in row]
                        while headers and not headers[-1]:
                            headers.pop()
                        return headers
        except Exception:
            pass

    # 5. Try pandas fallback
    try:
        import pandas as pd

        engine = (
            "calamine"
            if ext in [".xlsb", ".xls"]
            else ("openpyxl" if ext in [".xlsx", ".xlsm"] else None)
        )
        df = pd.read_excel(
            p, sheet_name=sheet_name, skiprows=expected_skiprows, nrows=1, engine=engine
        )
        headers = [str(c or "").strip() for c in df.columns]
        while headers and not headers[-1]:
            headers.pop()
        return headers
    except Exception:
        pass

    return []


@dataclass
class TemplateValidationReport:
    """Structured report returned by the pre-flight template validator."""

    is_valid: bool
    detected_format: str  # "OFFICIAL_KP_TEMPLATE_337", "LEGACY_SYNTHETIC", or "CUSTOM"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    register_columns_count: int = 0
    kplhiv_columns_count: int = 0
    encounters_detected: int = 0
    missing_core_columns: list[str] = field(default_factory=list)

    def summary_markdown(self) -> str:
        """Renders an executive summary of the template concordance status."""
        status_icon = "✅" if self.is_valid else "❌"
        lines = [
            f"### {status_icon} Template Concordance Audit: **{self.detected_format}**",
            f"- **Register Columns Detected:** `{self.register_columns_count}`",
            f"- **KPLHIV Columns Detected:** `{self.kplhiv_columns_count}`",
            f"- **Encounter Blocks Detected:** `{self.encounters_detected}` of 6",
        ]
        if self.errors:
            lines.append("\n**Blocking Errors:**")
            for err in self.errors:
                lines.append(f"- ❌ {err}")
        if self.warnings:
            lines.append("\n**Advisory Notices:**")
            for w in self.warnings:
                lines.append(f"- ⚠️ {w}")
        return "\n".join(lines)


def validate_kp_template_concordance(
    file_path: str | Path,
    expected_skiprows: int = 2,
) -> TemplateValidationReport:
    """Validates an uploaded workbook against the official KP Template specification.

    Guarantees zero-cell PII exposure: only sheet and column header metadata are audited.
    """
    p = Path(file_path).resolve()
    if not p.exists():
        return TemplateValidationReport(
            is_valid=False,
            detected_format="UNKNOWN",
            errors=[f"File not found on disk: {p.name}"],
        )

    try:
        available_sheets = get_workbook_sheet_names(p)
    except Exception as exc:
        return TemplateValidationReport(
            is_valid=False,
            detected_format="CORRUPT",
            errors=[f"Unable to read workbook structure: {exc}"],
        )

    # 1. Sheet existence check
    has_reg = any(
        s.strip().lower() in ["register", "fsw", "msm", "tg", "pwid", "vp"]
        for s in available_sheets
    )
    has_kp = any(
        "kplhiv" in s.strip().lower() or "plhiv" in s.strip().lower() for s in available_sheets
    )

    errors: list[str] = []
    warnings: list[str] = []

    if not has_reg:
        errors.append("Workbook is missing the required 'Register' worksheet.")
    if not has_kp:
        warnings.append("Workbook is missing the optional 'KPLHIV' tracking sheet.")

    if errors:
        return TemplateValidationReport(
            is_valid=False,
            detected_format="INVALID_SHEETS",
            errors=errors,
            warnings=warnings,
        )

    # Read header row metadata safely using multi-format extract_sheet_headers
    reg_sheet_name = next(
        s
        for s in available_sheets
        if s.strip().lower() in ["register", "fsw", "msm", "tg", "pwid", "vp"]
    )
    kp_sheet_name = next(
        (
            s
            for s in available_sheets
            if "kplhiv" in s.strip().lower() or "plhiv" in s.strip().lower()
        ),
        None,
    )

    raw_reg_headers = extract_sheet_headers(p, reg_sheet_name, expected_skiprows)
    raw_kp_headers = (
        extract_sheet_headers(p, kp_sheet_name, expected_skiprows) if kp_sheet_name else []
    )

    reg_cols_count = len(raw_reg_headers)
    kp_cols_count = len(raw_kp_headers)

    # Check demographic anchors
    norm_reg_headers = [normalize_token(h) for h in raw_reg_headers]
    has_uic = any("unique_identifier_code" in h or "uic" in h for h in norm_reg_headers)
    has_county = any("county" in h for h in norm_reg_headers)
    has_enrolment = any("enrolment" in h or "enrollment" in h for h in norm_reg_headers)

    missing_core = []
    if not has_uic:
        missing_core.append("KP/VP unique identifier code")
    if not has_county:
        missing_core.append("County")
    if not has_enrolment:
        missing_core.append("Date of enrolment")

    if missing_core:
        errors.append(
            f"Missing essential core demographic columns: {missing_core}. "
            "Please ensure row 3 contains the official template headers."
        )

    # Detect template format & encounter blocks
    if is_kp_template_register(raw_reg_headers):
        detected_format = "OFFICIAL_KP_TEMPLATE_337"
        encounters_detected = min(6, max(0, (reg_cols_count - 19) // 53))
        if reg_cols_count < 337:
            warnings.append(
                f"Register has {reg_cols_count} columns (expected 337 for all 6 encounters). "
                f"Detected {encounters_detected} complete encounter block(s)."
            )
    elif reg_cols_count >= 100:
        detected_format = "LEGACY_SYNTHETIC"
        encounters_detected = 6
    else:
        detected_format = "CUSTOM"
        encounters_detected = 1
        warnings.append(
            f"Uploaded register has {reg_cols_count} columns, differing from the 337-column official template. "
            "Pipeline will attempt fuzzy alias matching."
        )

    is_valid = len(errors) == 0

    return TemplateValidationReport(
        is_valid=is_valid,
        detected_format=detected_format,
        errors=errors,
        warnings=warnings,
        register_columns_count=reg_cols_count,
        kplhiv_columns_count=kp_cols_count,
        encounters_detected=encounters_detected,
        missing_core_columns=missing_core,
    )
