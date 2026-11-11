"""DQA exceptions exporter formatting validation results into openpyxl worksheets."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reporting.template_manager import ExcelTemplateConfig, get_template_manager

DQA_COLUMNS = [
    "Rule ID",
    "Severity",
    "UIC",
    "County",
    "Sub-Recipient",
    "Offending Columns",
    "Suggested Action",
]


def export_dqa_exceptions_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    exceptions_df: pd.DataFrame | None = None,
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """
    Renders DQA exceptions table into an openpyxl sheet.

    If exceptions_df is None or empty (0 exceptions), emits standard 7 column headers
    with an informational banner row per D-034:
    'No data quality exceptions detected. All records passed validation.'
    """
    if config is None:
        config = get_template_manager()

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

    header_font = Font(name=config.fonts.header, size=config.fonts.size, bold=True)
    body_font = Font(name=config.fonts.body, size=config.fonts.size, bold=False)
    thin_side = Side(style="thin", color="000000")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    clean_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = True
    ws.row_dimensions[1].height = 24

    # Write Headers
    col_widths = {1: 18, 2: 12, 3: 20, 4: 18, 5: 22, 6: 28, 7: 35}
    for c_idx, col_name in enumerate(DQA_COLUMNS, start=1):
        cell = ws.cell(row=1, column=c_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(c_idx)].width = col_widths.get(c_idx, 16)

    # Empty / Zero exceptions condition (D-034)
    if exceptions_df is None or exceptions_df.empty:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(DQA_COLUMNS))
        info_cell = ws.cell(
            row=2,
            column=1,
            value="No data quality exceptions detected. All records passed validation.",
        )
        info_cell.font = Font(name=config.fonts.body, size=11, bold=True, color="385723")
        info_cell.fill = clean_fill
        info_cell.alignment = Alignment(horizontal="center", vertical="center")
        for c in range(1, len(DQA_COLUMNS) + 1):
            ws.cell(row=2, column=c).border = thin_border
        ws.row_dimensions[2].height = 24
        return ws

    # Map column names if exceptions_df has standard validation columns
    col_map = {
        "rule_id": "Rule ID",
        "severity": "Severity",
        "uic": "UIC",
        "county": "County",
        "sr_name": "Sub-Recipient",
        "offending_columns": "Offending Columns",
        "suggested_action": "Suggested Action",
    }
    df = exceptions_df.rename(columns=col_map)

    # Populate exception rows
    for r_idx, (_, row) in enumerate(df.iterrows(), start=2):
        ws.row_dimensions[r_idx].height = 20
        severity_val = str(row.get("Severity", "")).upper()

        # Severity-based color tagging
        if "CRITICAL" in severity_val:
            row_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        elif "MAJOR" in severity_val:
            row_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        else:
            row_fill = None

        for c_idx, col_name in enumerate(DQA_COLUMNS, start=1):
            val = row.get(col_name, "")
            if isinstance(val, (list, tuple, set)):
                val = ", ".join(str(x) for x in val)
            elif pd.isna(val):
                val = ""

            cell = ws.cell(row=r_idx, column=c_idx, value=str(val))
            cell.font = body_font
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill
            cell.alignment = Alignment(
                horizontal="center" if c_idx in [1, 2] else "left",
                vertical="center",
            )

    return ws


def export_dqa_exceptions_workbook(
    exceptions_df: pd.DataFrame | None,
    output_path: Path | str,
    config: ExcelTemplateConfig | None = None,
) -> Path:
    """Exports standalone DQA exceptions workbook."""
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)

    export_dqa_exceptions_sheet(wb, "DQA_Exceptions", exceptions_df=exceptions_df, config=config)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
