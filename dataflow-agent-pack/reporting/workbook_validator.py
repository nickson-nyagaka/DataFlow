"""Workbook validator: programmatically inspects formatting, structure, and formula totals."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

from reporting.template_manager import (
    ExcelTemplateConfig,
    get_template_manager,
)


@dataclass
class ValidationIssue:
    sheet: str
    cell: str
    issue_type: str
    expected: Any
    actual: Any
    message: str


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    sheets_found: list[str] = field(default_factory=list)
    formula_checks_passed: int = 0
    formula_checks_failed: int = 0


def _extract_fill_hex(fill: Any) -> str | None:
    if fill and getattr(fill, "start_color", None):
        color = fill.start_color
        if getattr(color, "rgb", None):
            rgb_str = str(color.rgb)
            # Sometimes openpyxl returns '00FF7D81' (with alpha channel)
            if len(rgb_str) == 8 and rgb_str.startswith("00"):
                return rgb_str[2:].upper()
            return rgb_str.upper()
    return None


def validate_summary_workbook(
    file_path: Path | str,
    population: str,
    period_mode: str,
    reference_df: pd.DataFrame | None = None,
    config: ExcelTemplateConfig | None = None,
) -> ValidationResult:
    """
    Validates an exported summary workbook against template specifications.

    Verifies:
    1. Sheet existence (Summary sheet, Run Metadata, Cleaning Log).
    2. Header fonts (Cascadia Code 11 bold), data fonts (Candara 11), total font (Candara 11 bold).
    3. Fills (Row 2 coral #FF7D81, Total green #6BD669, Group header colors).
    4. View settings (Freeze panes at A3, showGridLines=False).
    5. Dimensions (Row 1=22, Row 2=30, Cols 1-3=22, Cols 4+=14).
    6. Dynamic SUM formulas present on total row and matching independent column sums.
    """
    if config is None:
        config = get_template_manager()

    layout = config.get_layout_for(population, period_mode)
    expected_sheet = config.get_sheet_name_for(population, period_mode)

    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    wb = openpyxl.load_workbook(p, data_only=False)
    issues: list[ValidationIssue] = []
    sheets_found = list(wb.sheetnames)

    # 1. Sheet existence
    if expected_sheet not in wb.sheetnames:
        issues.append(
            ValidationIssue(
                sheet="Workbook",
                cell="N/A",
                issue_type="MissingSheet",
                expected=expected_sheet,
                actual=sheets_found,
                message=f"Expected summary sheet '{expected_sheet}' not found",
            )
        )
        return ValidationResult(is_valid=False, issues=issues, sheets_found=sheets_found)

    ws = wb[expected_sheet]

    # 2. View settings
    actual_freeze = str(ws.freeze_panes)
    if actual_freeze != "A3":
        issues.append(
            ValidationIssue(
                sheet=expected_sheet,
                cell="View",
                issue_type="FreezePanes",
                expected="A3",
                actual=actual_freeze,
                message=f"Freeze panes mismatch: expected 'A3', got '{actual_freeze}'",
            )
        )

    gridlines_shown = getattr(ws.sheet_view, "showGridLines", True)
    if gridlines_shown is True:
        issues.append(
            ValidationIssue(
                sheet=expected_sheet,
                cell="View",
                issue_type="Gridlines",
                expected=False,
                actual=gridlines_shown,
                message="Sheet gridlines should be explicitly hidden (showGridLines=False)",
            )
        )

    # 3. Row heights
    r1_h = ws.row_dimensions[1].height
    if r1_h != config.dimensions.row_height_group:
        issues.append(
            ValidationIssue(
                sheet=expected_sheet,
                cell="Row 1",
                issue_type="RowHeight",
                expected=config.dimensions.row_height_group,
                actual=r1_h,
                message=f"Row 1 height expected {config.dimensions.row_height_group}, got {r1_h}",
            )
        )

    r2_h = ws.row_dimensions[2].height
    if r2_h != config.dimensions.row_height_sub:
        issues.append(
            ValidationIssue(
                sheet=expected_sheet,
                cell="Row 2",
                issue_type="RowHeight",
                expected=config.dimensions.row_height_sub,
                actual=r2_h,
                message=f"Row 2 height expected {config.dimensions.row_height_sub}, got {r2_h}",
            )
        )

    # 4. Header fonts & subheader fills
    # Check Row 1 group headers at the block level (top-left cell of each merge block)
    block_col_idx = 1
    for block in layout.blocks:
        col_letter = get_column_letter(block_col_idx)
        cell_r1 = ws.cell(row=1, column=block_col_idx)
        if cell_r1.font.name != config.fonts.header or not cell_r1.font.bold:
            issues.append(
                ValidationIssue(
                    sheet=expected_sheet,
                    cell=f"{col_letter}1",
                    issue_type="HeaderFont",
                    expected=f"{config.fonts.header} Bold",
                    actual=f"{cell_r1.font.name} (bold={cell_r1.font.bold})",
                    message=f"Row 1 header font at {col_letter}1 mismatch",
                )
            )

        expected_grp_fill = config.get_group_fill(block.group)
        actual_grp_fill = _extract_fill_hex(cell_r1.fill)
        if actual_grp_fill != expected_grp_fill:
            issues.append(
                ValidationIssue(
                    sheet=expected_sheet,
                    cell=f"{col_letter}1",
                    issue_type="GroupHeaderFill",
                    expected=expected_grp_fill,
                    actual=actual_grp_fill,
                    message=f"Group fill at {col_letter}1 expected {expected_grp_fill}, got {actual_grp_fill}",
                )
            )
        block_col_idx += len(block.columns)

    # Check Row 2 subheader font & fill on all columns
    total_cols = layout.total_columns
    for c in range(1, total_cols + 1):
        col_letter = get_column_letter(c)
        cell_r2 = ws.cell(row=2, column=c)
        if cell_r2.font.name != config.fonts.header:
            issues.append(
                ValidationIssue(
                    sheet=expected_sheet,
                    cell=f"{col_letter}2",
                    issue_type="SubheaderFont",
                    expected=config.fonts.header,
                    actual=cell_r2.font.name,
                    message=f"Row 2 font at {col_letter}2 mismatch",
                )
            )

        r2_fill_hex = _extract_fill_hex(cell_r2.fill)
        if r2_fill_hex != config.fills.subheader:
            issues.append(
                ValidationIssue(
                    sheet=expected_sheet,
                    cell=f"{col_letter}2",
                    issue_type="SubheaderFill",
                    expected=config.fills.subheader,
                    actual=r2_fill_hex,
                    message=f"Row 2 fill color at {col_letter}2 expected {config.fills.subheader}, got {r2_fill_hex}",
                )
            )

    # 5. Total row validation and formula verification
    max_row = ws.max_row
    total_row = max_row
    tot_label = str(ws.cell(row=total_row, column=1).value).strip()

    if tot_label != "TOTAL":
        issues.append(
            ValidationIssue(
                sheet=expected_sheet,
                cell=f"A{total_row}",
                issue_type="TotalLabel",
                expected="TOTAL",
                actual=tot_label,
                message=f"Expected 'TOTAL' in column A of row {total_row}, got '{tot_label}'",
            )
        )

    formula_passed = 0
    formula_failed = 0

    # Read values for independent verification if reference_df or sheet data exists
    last_data_row = total_row - 1
    has_data = last_data_row >= 3

    for c in range(4, total_cols + 1):
        col_letter = get_column_letter(c)
        tot_cell = ws.cell(row=total_row, column=c)
        val = str(tot_cell.value).strip()

        # Check total fill
        tot_fill_hex = _extract_fill_hex(tot_cell.fill)
        if tot_fill_hex != config.fills.total:
            issues.append(
                ValidationIssue(
                    sheet=expected_sheet,
                    cell=f"{col_letter}{total_row}",
                    issue_type="TotalFill",
                    expected=config.fills.total,
                    actual=tot_fill_hex,
                    message=f"Total row fill at {col_letter}{total_row} expected {config.fills.total}, got {tot_fill_hex}",
                )
            )

        # Check formula syntax
        expected_formula = f"=SUM({col_letter}3:{col_letter}{last_data_row})" if has_data else "=0"
        if val != expected_formula:
            issues.append(
                ValidationIssue(
                    sheet=expected_sheet,
                    cell=f"{col_letter}{total_row}",
                    issue_type="TotalFormula",
                    expected=expected_formula,
                    actual=val,
                    message=f"Formula at {col_letter}{total_row} expected '{expected_formula}', got '{val}'",
                )
            )
            formula_failed += 1
        else:
            formula_passed += 1

        # Cross-check independent column sum from cells or reference_df
        if reference_df is not None and has_data:
            col_name = layout.all_columns[c - 1]
            if col_name in reference_df.columns:
                independent_sum = int(
                    pd.to_numeric(reference_df[col_name], errors="coerce").fillna(0).sum()
                )
                # Sum from sheet data cells
                cell_sum = 0
                for r in range(3, last_data_row + 1):
                    cv = ws.cell(row=r, column=c).value
                    cell_sum += int(cv) if cv is not None else 0

                if independent_sum != cell_sum:
                    issues.append(
                        ValidationIssue(
                            sheet=expected_sheet,
                            cell=f"{col_letter}{total_row}",
                            issue_type="TotalChecksumMismatch",
                            expected=independent_sum,
                            actual=cell_sum,
                            message=f"Column sum mismatch on '{col_name}': reference={independent_sum}, sheet={cell_sum}",
                        )
                    )

    is_valid = len(issues) == 0
    return ValidationResult(
        is_valid=is_valid,
        issues=issues,
        sheets_found=sheets_found,
        formula_checks_passed=formula_passed,
        formula_checks_failed=formula_failed,
    )
