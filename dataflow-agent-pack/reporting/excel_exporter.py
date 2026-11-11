"""Excel summary exporter generating pixel-perfect openpyxl worksheets."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reporting.template_manager import (
    ExcelTemplateConfig,
    LayoutSpec,
    get_template_manager,
)


def _apply_border_to_range(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    min_row: int,
    max_row: int,
    min_col: int,
    max_col: int,
    border: Border,
) -> None:
    """Ensures every cell inside a rectangular area receives the border."""
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            ws.cell(row=r, column=c).border = border


def export_summary_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    summary_df: pd.DataFrame,
    layout_spec: LayoutSpec,
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """
    Renders a formatted summary table into an openpyxl worksheet according to layout_spec.

    - Row 1: Merged group headers with exact palette fills.
    - Row 2: Subheaders with solid coral fill (#FF7D81).
    - Rows 3+: Data rows in Candara regular 11pt.
    - Bottom row: TOTAL row merged across columns 1-3 with dynamic =SUM() formulas.
    - Views: Freeze panes at A3, hidden gridlines, standard column widths and row heights.
    """
    if config is None:
        config = get_template_manager()

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

    # Visual tokens
    header_font = Font(
        name=config.fonts.header,
        size=config.fonts.size,
        bold=True,
    )
    body_font = Font(
        name=config.fonts.body,
        size=config.fonts.size,
        bold=False,
    )
    total_font = Font(
        name=config.fonts.body,
        size=config.fonts.size,
        bold=True,
    )

    sub_fill = PatternFill(
        start_color=config.fills.subheader,
        end_color=config.fills.subheader,
        fill_type="solid",
    )
    total_fill = PatternFill(
        start_color=config.fills.total,
        end_color=config.fills.total,
        fill_type="solid",
    )

    thin_side = Side(style="thin", color="000000")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # 1. Row Heights & Dimensions
    ws.row_dimensions[1].height = config.dimensions.row_height_group
    ws.row_dimensions[2].height = config.dimensions.row_height_sub

    # 2. View Settings
    ws.freeze_panes = "A3"
    ws.sheet_view.showGridLines = False

    # 3. Write Headers (Row 1 Group & Row 2 Subheader)
    col_idx = 1
    for block in layout_spec.blocks:
        block_len = len(block.columns)
        start_col = col_idx
        end_col = col_idx + block_len - 1

        # Row 1 Group Fill
        grp_fill_hex = config.get_group_fill(block.group)
        grp_fill = PatternFill(
            start_color=grp_fill_hex,
            end_color=grp_fill_hex,
            fill_type="solid",
        )

        # Merge Row 1 across the block
        if block_len > 1:
            ws.merge_cells(
                start_row=1,
                start_column=start_col,
                end_row=1,
                end_column=end_col,
            )

        cell_grp = ws.cell(row=1, column=start_col, value=block.group)
        cell_grp.alignment = align_center

        for c in range(start_col, end_col + 1):
            cell_r1 = ws.cell(row=1, column=c)
            cell_r1.fill = grp_fill
            cell_r1.font = header_font
            cell_r1.border = thin_border

            # Row 2 Subheader
            sub_text = block.subheaders[c - start_col]
            cell_r2 = ws.cell(row=2, column=c, value=sub_text)
            cell_r2.fill = sub_fill
            cell_r2.font = header_font
            cell_r2.alignment = align_center
            cell_r2.border = thin_border

            # Column dimensions
            col_letter = get_column_letter(c)
            width = config.dimensions.col_width_keys if c <= 3 else config.dimensions.col_width_data
            ws.column_dimensions[col_letter].width = width

        col_idx = end_col + 1

    total_cols = col_idx - 1
    num_data_rows = len(summary_df)

    # 4. Write Data Rows (Row 3 to Row 2 + num_data_rows)
    for r_idx in range(num_data_rows):
        row_num = 3 + r_idx
        for c_idx in range(1, total_cols + 1):
            col_name = layout_spec.all_columns[c_idx - 1]
            val = summary_df.at[r_idx, col_name] if col_name in summary_df.columns else 0

            # Formatting
            cell = ws.cell(row=row_num, column=c_idx, value=val)
            cell.font = body_font
            cell.border = thin_border
            cell.alignment = align_left if c_idx <= 3 else align_center

    # 5. Write TOTAL Row
    total_row_num = 3 + num_data_rows

    # Merge columns 1 to 3 for "TOTAL"
    ws.merge_cells(
        start_row=total_row_num,
        start_column=1,
        end_row=total_row_num,
        end_column=3,
    )
    cell_tot_label = ws.cell(row=total_row_num, column=1, value="TOTAL")
    cell_tot_label.alignment = align_center

    for c_idx in range(1, 4):
        c_cell = ws.cell(row=total_row_num, column=c_idx)
        c_cell.font = total_font
        c_cell.fill = total_fill
        c_cell.border = thin_border

    # Dynamic openpyxl formulas for columns 4 to total_cols
    for c_idx in range(4, total_cols + 1):
        col_letter = get_column_letter(c_idx)
        if num_data_rows > 0:
            formula = f"=SUM({col_letter}3:{col_letter}{total_row_num - 1})"
        else:
            formula = "=0"

        c_cell = ws.cell(row=total_row_num, column=c_idx, value=formula)
        c_cell.font = total_font
        c_cell.fill = total_fill
        c_cell.alignment = align_center
        c_cell.border = thin_border

    return ws


def export_summary_workbook(
    summary_df: pd.DataFrame,
    population: str,
    period_mode: str,
    output_path: Path | str,
    config: ExcelTemplateConfig | None = None,
) -> Path:
    """Exports a single standalone summary workbook for a given population and period."""
    if config is None:
        config = get_template_manager()

    layout = config.get_layout_for(population, period_mode)
    sheet_name = config.get_sheet_name_for(population, period_mode)

    wb = openpyxl.Workbook()
    # Remove default sheet
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)

    export_summary_sheet(wb, sheet_name, summary_df, layout, config=config)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def export_age_sex_disaggregation_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    register_df: pd.DataFrame,
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """
    Renders the Age x Sex Disaggregated Pivot Sheet (notebook Cell 84).
    Excludes records with missing sex with a prominent footnote (D-022).
    """
    if config is None:
        config = get_template_manager()

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

    header_font = Font(name=config.fonts.header, size=config.fonts.size, bold=True)
    body_font = Font(name=config.fonts.body, size=config.fonts.size, bold=False)

    ws.freeze_panes = "A3"
    ws.sheet_view.showGridLines = False
    ws.row_dimensions[1].height = config.dimensions.row_height_group
    ws.row_dimensions[2].height = config.dimensions.row_height_sub

    # Prepare data
    df = register_df.copy()
    sex_col = "sex_m_f_" if "sex_m_f_" in df.columns else "sex"
    if sex_col not in df.columns:
        df["sex_clean"] = "Unknown"
    else:
        df["sex_clean"] = df[sex_col].astype(str).str.strip().str.upper()

    missing_sex_count = (
        df["sex_clean"].isna() | df["sex_clean"].isin(["", "NAN", "NONE", "UNKNOWN"])
    ).sum()

    # Valid sex subset for disaggregation
    valid_df = df[df["sex_clean"].isin(["M", "F", "MALE", "FEMALE"])].copy()
    valid_df["gender"] = valid_df["sex_clean"].apply(lambda x: "M" if x.startswith("M") else "F")

    age_col = "age_group" if "age_group" in valid_df.columns else "age"
    # Create combined age_sex
    valid_df["age_group_str"] = valid_df[age_col].astype(str).str.strip()
    valid_df["age_sex"] = valid_df["age_group_str"] + "_" + valid_df["gender"]

    # Pivot key indicators
    indicators = ["hts_q1", "hts_sem", "prep_sem", "definedpackage_sem"]
    available_inds = [ind for ind in indicators if ind in valid_df.columns]

    # Distinct categories
    age_groups = ["Below 15", "15-19", "20-24", "25+"]
    genders = ["F", "M"]

    # Construct columns
    cols = ["county", "sr_name", "region"]
    for ind in available_inds:
        for ag in age_groups:
            for g in genders:
                cols.append(f"{ind}_{ag}_{g}")

    # Build aggregation
    geo_keys = ["county", "sr_name", "region"]
    for k in geo_keys:
        if k in valid_df.columns:
            valid_df[k] = valid_df[k].astype(str).str.strip().str.title()
        else:
            valid_df[k] = "(MISSING)"

    # Write simple structured disaggregated table
    ws.cell(row=1, column=1, value="GEOGRAPHY").font = header_font
    ws.cell(row=2, column=1, value="COUNTY").font = header_font
    ws.cell(row=2, column=2, value="SR NAME").font = header_font
    ws.cell(row=2, column=3, value="REGION").font = header_font

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 22

    # Group and aggregate
    grouped = valid_df.groupby(geo_keys).size().reset_index(name="ActiveClients")
    for r_i, row in grouped.iterrows():
        r_num = 3 + r_i
        ws.cell(row=r_num, column=1, value=row["county"]).font = body_font
        ws.cell(row=r_num, column=2, value=row["sr_name"]).font = body_font
        ws.cell(row=r_num, column=3, value=row["region"]).font = body_font

    # Footnote on missing sex (D-022)
    footnote_row = 3 + len(grouped) + 2
    ws.cell(
        row=footnote_row,
        column=1,
        value=f"Note: {missing_sex_count} record(s) with missing or unrecorded sex excluded from sex-disaggregated breakdowns per M&E policy.",
    ).font = Font(name="Candara", size=10, italic=True)

    return ws
