"""Cleaned data exporter with fast vectorized identifier masking and streaming writes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reporting.template_manager import ExcelTemplateConfig, get_template_manager

IDENTIFIER_COLUMNS = [
    "kp_vp_unique_identifier_code",
    "kp_vp_unique_identifier_code_",
    "uic",
    "program_uic",
    "client_uic",
    "ccc_number_nupi_n_a_10_digit_number_",
    "ccc_number",
    "ccc_no",
    "nupi_number",
    "nupi",
]


def mask_identifier(val: Any) -> str:
    """Computes a deterministic salted 8-character pseudo-hash MASK-XXXX (D-035)."""
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if not s or s.upper() in ["NAN", "NONE", "UNKNOWN", "(MISSING)"]:
        return ""
    h = hashlib.sha256(f"DATAFLOW_SALT_{s}".encode()).hexdigest()[:6].upper()
    return f"MASK-{h}"


def apply_identifier_masking(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a copy of the dataframe with all sensitive identifier columns masked."""
    out = df.copy()
    for col in out.columns:
        col_clean = str(col).lower().strip()
        if any(id_col in col_clean for id_col in IDENTIFIER_COLUMNS):
            # Fast dictionary map over unique values
            s = out[col].astype(str).str.strip()
            unique_vals = s.unique()
            val_map = {
                v: mask_identifier(v)
                for v in unique_vals
                if str(v) and str(v).upper() not in ["NAN", "NONE", "UNKNOWN", "(MISSING)"]
            }
            out[col] = s.map(val_map).fillna("")
    return out


def export_dataframe_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    df: pd.DataFrame,
    mask_identifiers: bool = False,
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """Renders a dataframe into an openpyxl worksheet with high performance streaming."""
    if config is None:
        config = get_template_manager()

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

    data = apply_identifier_masking(df) if mask_identifiers else df.copy()

    header_font = Font(name=config.fonts.header, size=config.fonts.size, bold=True)
    thin_side = Side(style="thin", color="000000")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    header_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = True
    ws.row_dimensions[1].height = 24

    # 1. Write styled header row
    cols = list(data.columns)
    for c_idx, col in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=c_idx, value=str(col))
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center")
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = max(min(len(str(col)) + 4, 30), 14)

    # 2. Fast streaming row append (100x faster than cell-by-cell styling for large frames)
    # Replace NaNs with empty string
    clean_data = data.astype(object).fillna("")
    for row in clean_data.itertuples(index=False, name=None):
        ws.append(list(row))

    return ws


def export_cleaned_data_workbook(
    cleaned_register: pd.DataFrame,
    cleaned_kplhiv: pd.DataFrame,
    output_path: Path | str,
    mask_identifiers: bool = False,
    config: ExcelTemplateConfig | None = None,
) -> Path:
    """Exports standalone Cleaned Cohort Data workbook with Register and KPLHIV tabs."""
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)

    export_dataframe_sheet(
        wb,
        "Cleaned Register",
        cleaned_register,
        mask_identifiers=mask_identifiers,
        config=config,
    )
    export_dataframe_sheet(
        wb,
        "Cleaned KPLHIV",
        cleaned_kplhiv,
        mask_identifiers=mask_identifiers,
        config=config,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
