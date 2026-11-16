"""Pre-Processing Template Concordance Validator for DATAFLOW.

Audits uploaded workbooks against the official Kenya KP Cohort Register template (reference/KP_TEMPLATE.xlsx)
BEFORE analytical calculations, DQA, or reporting packages are executed.
"""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from core.ingestion import detect_header_skiprows, get_workbook_sheet_names, normalize_token
from core.template_schema import find_encounter_block_starts, is_kp_template_register


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


def inspect_sheet_data_rows(p: Path, sheet_name: str, header_skiprows: int) -> int:
    """Inspects whether a worksheet has non-blank data rows below the header row without loading full dataset."""
    ext = p.suffix.lower()

    # 1. Calamine fast inspection
    try:
        from python_calamine import CalamineWorkbook

        wb = CalamineWorkbook.from_path(str(p))
        matches = [s for s in wb.sheet_names if s.strip().lower() == sheet_name.strip().lower()]
        if matches:
            ws = wb.get_sheet_by_name(matches[0])
            count = 0
            for idx, row in enumerate(ws.iter_rows()):
                if idx > header_skiprows:
                    if any(cell is not None and str(cell).strip() != "" for cell in row):
                        count += 1
                        if count >= 3:
                            break
            return count
    except Exception:
        pass

    # 2. openpyxl inspection
    if ext in [".xlsx", ".xlsm"]:
        try:
            import openpyxl

            wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
            matches = [s for s in wb.sheetnames if s.strip().lower() == sheet_name.strip().lower()]
            if matches:
                ws = wb[matches[0]]
                count = 0
                for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                    if row_idx > header_skiprows:
                        if any(c is not None and str(c).strip() != "" for c in row):
                            count += 1
                            if count >= 3:
                                break
                wb.close()
                return count
            wb.close()
        except Exception:
            pass

    # 3. pandas fallback
    try:
        engine = "calamine" if ext in [".xlsb", ".xls"] else ("openpyxl" if ext in [".xlsx", ".xlsm"] else None)
        df = pd.read_excel(p, sheet_name=sheet_name, skiprows=header_skiprows, nrows=3, engine=engine)
        return len(df.dropna(how="all"))
    except Exception:
        return 0


@dataclass
class ValidationCheckItem:
    """Represents a discrete row in the workbook validation report."""

    worksheet: str
    check_name: str
    status: str  # "Passed", "Warning", "Failed"
    problem: str
    recommended_action: str


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
    items: list[ValidationCheckItem] = field(default_factory=list)
    missing_sheets: list[str] = field(default_factory=list)
    detected_sheets: list[str] = field(default_factory=list)
    reg_sheet_name: str | None = None
    kp_sheet_name: str | None = None

    def to_dataframe(self) -> pd.DataFrame:
        """Converts audit items into standardized DataFrame table."""
        records = [
            {
                "Worksheet": item.worksheet,
                "Validation check": item.check_name,
                "Status": item.status,
                "Problem": item.problem,
                "Recommended action": item.recommended_action,
            }
            for item in self.items
        ]
        return pd.DataFrame(records)

    def to_csv_bytes(self) -> bytes:
        """Exports validation report as CSV bytes with UTF-8 BOM."""
        df = self.to_dataframe()
        return df.to_csv(index=False).encode("utf-8-sig")

    def to_excel_bytes(self) -> bytes:
        """Exports validation report as formatted Excel workbook bytes."""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            self.to_dataframe().to_excel(writer, index=False, sheet_name="Validation Report")
        return output.getvalue()

    def actionable_error_markdown(self) -> str:
        """Generates clear, actionable error markdown matching DataFlow standard requirements."""
        lines = [
            "### ❌ Workbook Validation Failed",
            "",
            "Your uploaded workbook does not match the required DataFlow template.",
            "",
        ]

        if self.missing_sheets:
            lines.extend([
                "**The following required worksheets are missing:**",
                *[f"- `{s}`" for s in self.missing_sheets],
                "",
                "**How to fix this:**",
                "1. Open your Excel workbook.",
                "2. Ensure it contains worksheets named `Register` and `KPLHIV` (or approved typology equivalents).",
                "3. Copy the correct data into their respective worksheets.",
                "4. Ensure worksheet names are spelled accurately without trailing spaces.",
                "5. Save the workbook and upload it again.",
                "",
                "**Processing cannot continue until these required worksheets are available.**",
            ])
            return "\n".join(lines)

        if self.missing_core_columns:
            target_sheet = self.reg_sheet_name or "Register"
            lines.extend([
                f"- **Worksheet:** `{target_sheet}`",
                f"- **Missing required columns:** {', '.join(f'`{c}`' for c in self.missing_core_columns)}",
                f"- **Action:** Check the workbook against the approved DataFlow template and restore the missing columns.",
                "",
                "**How to fix this:**",
                "1. Open your Excel workbook.",
                f"2. Navigate to the `{target_sheet}` worksheet.",
                f"3. Ensure row 3 contains the required column headers ({', '.join(self.missing_core_columns)}).",
                "4. Check that column names are not empty or displaced to another row.",
                "5. Save the workbook and upload it again.",
                "",
                "**Processing cannot continue until these required columns are available.**",
            ])
            return "\n".join(lines)

        # Other failures (e.g. empty worksheet, corrupted structure)
        failed_items = [it for it in self.items if it.status == "Failed"]
        if failed_items:
            for it in failed_items:
                lines.extend([
                    f"- **Worksheet:** `{it.worksheet}`",
                    f"- **Problem:** {it.problem}",
                    f"- **Action:** {it.recommended_action}",
                    "",
                ])
            lines.append("**Processing cannot continue until these issues are resolved.**")
            return "\n".join(lines)

        if self.errors:
            lines.extend([
                "**Issues detected:**",
                *[f"- {e}" for e in self.errors],
                "",
                "**Processing cannot continue until the workbook structure is corrected.**",
            ])
            return "\n".join(lines)

        return "\n".join(lines)

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
    population: str = "FSW",
) -> TemplateValidationReport:
    """Validates an uploaded workbook against the official KP Template specification.

    Performs comprehensive structural, column, and data-presence checks.
    Guarantees zero-cell PII exposure: only sheet and column header metadata are audited.
    """
    p = Path(file_path).resolve()
    ext = p.suffix.lower()

    items: list[ValidationCheckItem] = []
    errors: list[str] = []
    warnings: list[str] = []

    # 1. File existence & format check
    if not p.exists():
        items.append(
            ValidationCheckItem(
                worksheet="Workbook",
                check_name="File existence",
                status="Failed",
                problem=f"File not found on disk: {p.name}",
                recommended_action="Ensure the file was uploaded completely and re-upload.",
            )
        )
        return TemplateValidationReport(
            is_valid=False,
            detected_format="UNKNOWN",
            errors=[f"File not found on disk: {p.name}"],
            items=items,
        )

    valid_extensions = {".xlsx", ".xlsb", ".xlsm", ".xls", ".csv"}
    if ext not in valid_extensions:
        items.append(
            ValidationCheckItem(
                worksheet="Workbook",
                check_name="Workbook format",
                status="Failed",
                problem=f"Unsupported format '{ext}'. Expected .xlsx, .xlsb, or .csv.",
                recommended_action="Save your file as an Excel Workbook (.xlsx) or Binary Workbook (.xlsb) and re-upload.",
            )
        )
        return TemplateValidationReport(
            is_valid=False,
            detected_format="INVALID_FORMAT",
            errors=[f"Unsupported file format: {ext}"],
            items=items,
        )

    items.append(
        ValidationCheckItem(
            worksheet="Workbook",
            check_name="Workbook format",
            status="Passed",
            problem="None",
            recommended_action="None",
        )
    )

    try:
        available_sheets = get_workbook_sheet_names(p)
    except Exception as exc:
        items.append(
            ValidationCheckItem(
                worksheet="Workbook",
                check_name="Workbook readability",
                status="Failed",
                problem=f"Unable to read workbook structure: {exc}",
                recommended_action="Ensure the workbook is not password-protected or corrupted. Re-save in Excel.",
            )
        )
        return TemplateValidationReport(
            is_valid=False,
            detected_format="CORRUPT",
            errors=[f"Unable to read workbook structure: {exc}"],
            items=items,
        )

    # 2. Worksheet names and naming inconsistencies
    for s in available_sheets:
        if s != s.strip():
            items.append(
                ValidationCheckItem(
                    worksheet=s,
                    check_name="Worksheet naming conventions",
                    status="Warning",
                    problem=f"Worksheet '{s}' contains extraneous leading or trailing spaces.",
                    recommended_action="Trim extra spaces from worksheet names in Excel for clean matching.",
                )
            )

    # 3. Sheet existence check
    pop_lower = population.strip().lower()
    reg_candidates = [
        "register",
        pop_lower,
    ]
    has_reg = any(any(cand in s.strip().lower() for cand in reg_candidates) for s in available_sheets)
    has_kp = any("kplhiv" in s.strip().lower() for s in available_sheets)

    missing_sheets: list[str] = []
    if not has_reg:
        missing_sheets.append("Register")
        errors.append("Workbook is missing the required 'Register' worksheet.")
        items.append(
            ValidationCheckItem(
                worksheet="Register",
                check_name="Required worksheet",
                status="Failed",
                problem="Missing required 'Register' worksheet.",
                recommended_action="Add a worksheet named 'Register' (or matching population name) containing client encounters.",
            )
        )
    else:
        items.append(
            ValidationCheckItem(
                worksheet="Register",
                check_name="Required worksheet",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )

    if not has_kp:
        warnings.append("Workbook does not contain a dedicated 'KPLHIV' tracking sheet.")
        items.append(
            ValidationCheckItem(
                worksheet="KPLHIV",
                check_name="Required worksheet",
                status="Warning",
                problem="Optional KPLHIV tracking sheet not detected.",
                recommended_action="Ensure KPLHIV tracking worksheet is included if reporting 95-95-95 clinical cascade data.",
            )
        )
    else:
        items.append(
            ValidationCheckItem(
                worksheet="KPLHIV",
                check_name="Required worksheet",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )

    if not has_reg:
        return TemplateValidationReport(
            is_valid=False,
            detected_format="INVALID_SHEETS",
            errors=errors,
            warnings=warnings,
            items=items,
            missing_sheets=missing_sheets,
            detected_sheets=available_sheets,
        )

    # Identify primary sheets
    reg_sheet_name = next(
        s
        for s in available_sheets
        if any(cand in s.strip().lower() for cand in reg_candidates)
    )
    kp_sheet_name = next(
        (
            s
            for s in available_sheets
            if "kplhiv" in s.strip().lower()
        ),
        None,
    )

    # 4. Header row position & detection
    detected_skiprows = detect_header_skiprows(p, reg_sheet_name, fallback_skiprows=expected_skiprows)
    if detected_skiprows != expected_skiprows:
        warnings.append(
            f"Register header row detected at row {detected_skiprows + 1} instead of standard template row {expected_skiprows + 1}."
        )
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Header position alignment",
                status="Warning",
                problem=f"Headers detected at row {detected_skiprows + 1} (template expects row {expected_skiprows + 1}).",
                recommended_action=f"Auto-detection will adjust skiprows={detected_skiprows}. For standard alignment, place headers at row {expected_skiprows + 1}.",
            )
        )
    else:
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Header position alignment",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )

    # Extract headers
    effective_skiprows = detected_skiprows if detected_skiprows is not None else expected_skiprows
    raw_reg_headers = extract_sheet_headers(p, reg_sheet_name, effective_skiprows)
    raw_kp_headers = extract_sheet_headers(p, kp_sheet_name, effective_skiprows) if kp_sheet_name else []

    reg_cols_count = len(raw_reg_headers)
    kp_cols_count = len(raw_kp_headers)

    # 5. Duplicate or conflicting column names
    clean_headers = [str(h).strip() for h in raw_reg_headers if h and str(h).strip()]
    header_counts = Counter(clean_headers)
    duplicates = [h for h, cnt in header_counts.items() if cnt > 1]
    if duplicates:
        warnings.append(f"Duplicate column headers detected in Register: {duplicates[:4]}.")
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Duplicate column names",
                status="Warning",
                problem=f"Duplicate column headers detected: {duplicates[:4]}",
                recommended_action="Disambiguate duplicate columns in Excel so each indicator column is uniquely named.",
            )
        )
    else:
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Duplicate column names",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )

    # 6. Required columns & expected column structures
    norm_reg_headers = [normalize_token(h) for h in raw_reg_headers]
    has_uic = any("unique_identifier_code" in h or "uic" in h for h in norm_reg_headers)
    has_county = any("county" in h for h in norm_reg_headers)
    has_enrolment = any("enrolment" in h or "enrollment" in h for h in norm_reg_headers)

    missing_core = []
    if not has_uic:
        missing_core.append("kp_vp_unique_identifier_code")
    if not has_county:
        missing_core.append("county")
    if not has_enrolment:
        missing_core.append("date_of_enrolment")

    if missing_core:
        errors.append(
            f"Missing essential core demographic columns in Register: {missing_core}."
        )
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Required columns",
                status="Failed",
                problem=f"Missing essential columns: {', '.join(missing_core)}",
                recommended_action=f"Restore {', '.join(missing_core)} to the header row in worksheet '{reg_sheet_name}'.",
            )
        )
    else:
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Required columns",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )

    # 7. Empty worksheets check (verifying non-blank data rows exist)
    reg_rows = inspect_sheet_data_rows(p, reg_sheet_name, effective_skiprows)
    if reg_rows == 0:
        errors.append(f"Worksheet '{reg_sheet_name}' is empty and contains zero client records.")
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Data records presence",
                status="Failed",
                problem=f"Worksheet '{reg_sheet_name}' contains no client records (empty worksheet).",
                recommended_action="Paste client encounter records below the header row before uploading.",
            )
        )
    else:
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Data records presence",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )

    # 8. Encounter blocks and template format detection
    starts = find_encounter_block_starts(raw_reg_headers)
    if is_kp_template_register(raw_reg_headers):
        detected_format = "OFFICIAL_KP_TEMPLATE_337"
        first_enc = starts[0] if starts else 19
        encounters_detected = min(6, len(starts)) if len(starts) >= 1 else min(6, max(0, (reg_cols_count - first_enc) // 53))
        if reg_cols_count < 330:
            warnings.append(
                f"Register has {reg_cols_count} columns (expected ~337 for all 6 encounters). "
                f"Detected {encounters_detected} complete encounter block(s)."
            )
            items.append(
                ValidationCheckItem(
                    worksheet=reg_sheet_name,
                    check_name="Encounter blocks structure",
                    status="Warning",
                    problem=f"Detected {encounters_detected} of 6 encounter blocks ({reg_cols_count} columns).",
                    recommended_action="Verify if truncated encounters affect subsequent period reporting.",
                )
            )
        else:
            items.append(
                ValidationCheckItem(
                    worksheet=reg_sheet_name,
                    check_name="Encounter blocks structure",
                    status="Passed",
                    problem="None",
                    recommended_action="None",
                )
            )
    elif reg_cols_count >= 100:
        detected_format = "LEGACY_SYNTHETIC"
        encounters_detected = 6
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Encounter blocks structure",
                status="Passed",
                problem="None",
                recommended_action="None",
            )
        )
    else:
        detected_format = "CUSTOM"
        encounters_detected = 1
        warnings.append(
            f"Uploaded register has {reg_cols_count} columns, differing from the 337-column official template. "
            "Pipeline will attempt fuzzy alias matching."
        )
        items.append(
            ValidationCheckItem(
                worksheet=reg_sheet_name,
                check_name="Template structure",
                status="Warning",
                problem=f"Custom layout with {reg_cols_count} columns detected.",
                recommended_action="Concordance relies on column alias mapping. Use standard template for optimal compatibility.",
            )
        )

    is_valid = not any(it.status == "Failed" for it in items)

    return TemplateValidationReport(
        is_valid=is_valid,
        detected_format=detected_format,
        errors=errors,
        warnings=warnings,
        register_columns_count=reg_cols_count,
        kplhiv_columns_count=kp_cols_count,
        encounters_detected=encounters_detected,
        missing_core_columns=missing_core,
        items=items,
        missing_sheets=missing_sheets,
        detected_sheets=available_sheets,
        reg_sheet_name=reg_sheet_name,
        kp_sheet_name=kp_sheet_name,
    )
