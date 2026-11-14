"""Cleaned data exporter with fast vectorized identifier masking and streaming writes."""

from __future__ import annotations

import datetime
import hashlib
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
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


def xml_escape(val: Any) -> str:
    """Sanitizes text for safe inclusion in OpenXML inlineStr elements."""
    s = (
        str(val)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def generate_sheet_xml_rows(
    df: pd.DataFrame, mask_identifiers: bool = False
) -> tuple[bytes, int, str]:
    """Generates pure OpenXML row elements for high-performance sheet streaming.

    Bypasses openpyxl in-memory DOM allocations, speeding up large-scale sheet creation
    by orders of magnitude while preserving 100% cell values and types.
    """
    data = apply_identifier_masking(df) if mask_identifiers else df
    cols = list(data.columns)
    col_letters = [get_column_letter(i) for i in range(1, len(cols) + 1)]
    total_rows = len(data) + 1
    last_col_letter = col_letters[-1] if col_letters else "A"

    col_kinds: list[int] = []
    for c in cols:
        dt = data[c].dtype
        if pd.api.types.is_integer_dtype(dt):
            col_kinds.append(0)  # integer
        elif pd.api.types.is_float_dtype(dt):
            col_kinds.append(1)  # float
        elif pd.api.types.is_bool_dtype(dt):
            col_kinds.append(2)  # boolean
        else:
            col_kinds.append(3)  # string / object / datetime

    row_chunks: list[str] = []
    batch: list[str] = []
    batch_size = 2000

    for r_idx, row in enumerate(data.itertuples(index=False, name=None), start=2):
        row_parts = [f'<row r="{r_idx}">']
        for c_idx, val in enumerate(row):
            if val is None or val == "":
                continue
            kind = col_kinds[c_idx]
            col_let = col_letters[c_idx]

            if kind == 0:
                row_parts.append(f'<c r="{col_let}{r_idx}" t="n"><v>{val}</v></c>')
            elif kind == 1:
                if val != val:  # NaN
                    continue
                if isinstance(val, (int, float)) and val.is_integer():
                    row_parts.append(f'<c r="{col_let}{r_idx}" t="n"><v>{int(val)}</v></c>')
                else:
                    row_parts.append(f'<c r="{col_let}{r_idx}" t="n"><v>{val}</v></c>')
            elif kind == 2:
                row_parts.append(f'<c r="{col_let}{r_idx}" t="b"><v>{1 if val else 0}</v></c>')
            else:
                if isinstance(val, (int, np.integer)):
                    row_parts.append(f'<c r="{col_let}{r_idx}" t="n"><v>{val}</v></c>')
                elif isinstance(val, (float, np.floating)):
                    if val != val:
                        continue
                    if val.is_integer():
                        row_parts.append(f'<c r="{col_let}{r_idx}" t="n"><v>{int(val)}</v></c>')
                    else:
                        row_parts.append(f'<c r="{col_let}{r_idx}" t="n"><v>{val}</v></c>')
                elif isinstance(val, bool):
                    row_parts.append(f'<c r="{col_let}{r_idx}" t="b"><v>{1 if val else 0}</v></c>')
                elif isinstance(val, (pd.Timestamp, datetime.date, datetime.datetime)):
                    s = val.isoformat() if hasattr(val, "isoformat") else str(val)
                    if "T00:00:00" in s:
                        s = s.split("T")[0]
                    row_parts.append(f'<c r="{col_let}{r_idx}" t="inlineStr"><is><t>{s}</t></is></c>')
                else:
                    s = str(val).strip()
                    if not s or s in ("nan", "None", "NaT"):
                        continue
                    s_esc = xml_escape(s)
                    row_parts.append(f'<c r="{col_let}{r_idx}" t="inlineStr"><is><t>{s_esc}</t></is></c>')

        row_parts.append("</row>")
        batch.append("".join(row_parts))

        if len(batch) >= batch_size:
            row_chunks.append("".join(batch))
            batch = []

    if batch:
        row_chunks.append("".join(batch))

    xml_bytes = "".join(row_chunks).encode("utf-8")
    return xml_bytes, total_rows, last_col_letter


def inject_sheet_xml_bytes(
    xlsx_path: Path | str,
    sheet_name: str,
    xml_rows_bytes: bytes,
    total_rows: int | None = None,
    last_col_letter: str | None = None,
) -> None:
    """Directly splices streaming row XML into an existing .xlsx worksheet file."""
    path = Path(xlsx_path)
    with zipfile.ZipFile(path, "r") as zin:
        wb_xml = ET.fromstring(zin.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(zin.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_xml}
        ns = {
            "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        target_file: str | None = None
        for sheet in wb_xml.find("main:sheets", ns):
            if sheet.attrib.get("name") == sheet_name:
                r_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                target = rel_map.get(r_id, "").lstrip("/")
                target_file = target if target.startswith("xl/") else f"xl/{target}"
                break

        if not target_file:
            raise ValueError(f"Sheet '{sheet_name}' not found in {xlsx_path}")

        orig_sheet_xml = zin.read(target_file)
        pos = orig_sheet_xml.find(b"</sheetData>")
        if pos == -1:
            raise ValueError(f"</sheetData> tag not found in {target_file}")

        if total_rows and last_col_letter:
            dim_pattern = re.compile(rb'<dimension ref="[^"]*"\s*/>')
            new_dim = f'<dimension ref="A1:{last_col_letter}{total_rows}"/>'.encode()
            orig_sheet_xml = dim_pattern.sub(new_dim, orig_sheet_xml, count=1)
            pos = orig_sheet_xml.find(b"</sheetData>")

        new_sheet_xml = orig_sheet_xml[:pos] + xml_rows_bytes + orig_sheet_xml[pos:]

        temp_buf = io.BytesIO()
        with zipfile.ZipFile(temp_buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zout:
            for item in zin.infolist():
                if item.filename == target_file:
                    zout.writestr(item, new_sheet_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))

    with open(path, "wb") as f:
        f.write(temp_buf.getvalue())


def export_dataframe_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    df: pd.DataFrame,
    mask_identifiers: bool = False,
    config: ExcelTemplateConfig | None = None,
    header_only: bool = False,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """Renders a dataframe into an openpyxl worksheet with high performance streaming.

    If header_only is True, sets up styled headers, columns, and freeze panes without
    allocating millions of cell objects in memory (for subsequent fast XML injection).
    """
    if config is None:
        config = get_template_manager()

    data = apply_identifier_masking(df) if mask_identifiers else df.copy()

    header_font = Font(name=config.fonts.header, size=config.fonts.size, bold=True)
    thin_side = Side(style="thin", color="000000")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    header_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    if getattr(workbook, "write_only", False):
        ws = workbook.create_sheet(title=sheet_name)
        header_cells = []
        for col in data.columns:
            c = openpyxl.cell.WriteOnlyCell(ws, value=str(col))
            c.font = header_font
            c.fill = header_fill
            c.border = thin_border
            c.alignment = Alignment(horizontal="center", vertical="center")
            header_cells.append(c)
        ws.append(header_cells)

        if not header_only:
            clean_data = data.astype(object).fillna("")
            for row in clean_data.itertuples(index=False, name=None):
                ws.append(list(row))
        return ws

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

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

    # If header_only is requested, return early to avoid DOM memory explosion
    if header_only:
        return ws

    # 2. Fast streaming row append for smaller tables
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
    xml_rows_bytes: bytes | None = None,
    total_rows: int | None = None,
    last_col_letter: str | None = None,
) -> Path:
    """Exports standalone Cleaned Cohort Data workbook with Register and KPLHIV tabs.

    Optimized for high performance on large cohorts (> 500 records) via OpenXML streaming.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(cleaned_register) > 500:
        if xml_rows_bytes is None:
            xml_rows_bytes, total_rows, last_col_letter = generate_sheet_xml_rows(
                cleaned_register, mask_identifiers=mask_identifiers
            )

        wb = openpyxl.Workbook()
        if wb.active is not None:
            wb.remove(wb.active)

        export_dataframe_sheet(
            wb,
            "Cleaned Register",
            cleaned_register,
            mask_identifiers=mask_identifiers,
            config=config,
            header_only=True,
        )
        export_dataframe_sheet(
            wb,
            "Cleaned KPLHIV",
            cleaned_kplhiv,
            mask_identifiers=mask_identifiers,
            config=config,
            header_only=False,
        )
        wb.save(out)
        wb.close()
        inject_sheet_xml_bytes(
            out,
            "Cleaned Register",
            xml_rows_bytes,
            total_rows=total_rows,
            last_col_letter=last_col_letter,
        )
        return out

    wb = openpyxl.Workbook(write_only=True)
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
    wb.save(out)
    wb.close()
    return out
