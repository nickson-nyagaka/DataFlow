"""Excel summary exporter generating pixel-perfect openpyxl worksheets."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from analytics.demographics import compute_kpi_demographic_summary
from core.population_rules import get_typology_subheaders
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
    population: str = "TG",
    period_mode: str = "Q1",
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """Renders the typology-aware KPI Indicators by Age and Sex table.

    Disaggregates DEFINED PACKAGE, HTS, and PREP across typology-specific age-sex groups and totals:
    - FSW: 15 columns total (Cols A-O) with Female-only columns
    - MSM: 15 columns total (Cols A-O) with Male-only columns
    - PWID / TG / VP: 24 columns total (Cols A-X) with both sexes
    """
    if config is None:
        config = get_template_manager()

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

    # Compute KPI Demographic DataFrame
    kpi_df = compute_kpi_demographic_summary(
        register_df, population=population, period_mode=period_mode
    )

    header_font_white = Font(name=config.fonts.header, size=config.fonts.size, bold=True, color="FFFFFF")
    header_font_black = Font(name=config.fonts.header, size=config.fonts.size, bold=True, color="000000")
    body_font = Font(name=config.fonts.body, size=config.fonts.size, bold=False)
    total_font = Font(name=config.fonts.body, size=config.fonts.size, bold=True)

    fill_demo = PatternFill(start_color="00B050", end_color="00B050", fill_type="solid")
    fill_def = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")
    fill_hts = PatternFill(start_color="F79646", end_color="F79646", fill_type="solid")
    fill_prep = PatternFill(start_color="FCD5B5", end_color="FCD5B5", fill_type="solid")
    fill_total = PatternFill(start_color="92D050", end_color="92D050", fill_type="solid")
    fill_zebra = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    thin_side = Side(style="thin", color="B0B0B0")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.freeze_panes = "A3"
    ws.sheet_view.showGridLines = False
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 30

    # Dynamic typology-aware subheader and column boundaries
    age_sex_labels = get_typology_subheaders(population)
    cols_per_ind = len(age_sex_labels)
    total_cols = 3 + 3 * cols_per_ind

    # Column widths
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 18
    for col_i in range(4, total_cols + 1):
        ws.column_dimensions[get_column_letter(col_i)].width = 12

    # Row 1 Group Headers
    def_start = 4
    def_end = 3 + cols_per_ind
    hts_start = def_end + 1
    hts_end = def_end + cols_per_ind
    prep_start = hts_end + 1
    prep_end = total_cols

    groups = [
        ("DEMOGRAPHICS", 1, 3, fill_demo, header_font_white),
        ("DEFINED PACKAGE", def_start, def_end, fill_def, header_font_white),
        ("HTS", hts_start, hts_end, fill_hts, header_font_white),
        ("PREP", prep_start, prep_end, fill_prep, header_font_black),
    ]

    for title, start_col, end_col, fill, font in groups:
        ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
        cell = ws.cell(1, start_col, value=title)
        cell.font = font
        cell.fill = fill
        cell.alignment = align_center
        for c in range(start_col, end_col + 1):
            ws.cell(1, c).border = thin_border
            ws.cell(1, c).fill = fill

    # Row 2 Subheaders
    subheaders = [
        ("SR  NAME", fill_demo, header_font_white),
        ("REGION", fill_demo, header_font_white),
        ("COUNTY", fill_demo, header_font_white),
    ]
    for lbl in age_sex_labels:
        subheaders.append((lbl, fill_def, header_font_white))
    for lbl in age_sex_labels:
        subheaders.append((lbl, fill_hts, header_font_white))
    for lbl in age_sex_labels:
        subheaders.append((lbl, fill_prep, header_font_black))

    for c_idx, (lbl, fill, font) in enumerate(subheaders, start=1):
        cell = ws.cell(2, c_idx, value=lbl)
        cell.border = thin_border
        cell.fill = fill
        cell.font = font
        cell.alignment = align_center

    total_col_indices = {def_end, hts_end, prep_end}

    # Rows 3+ Data Rows
    for r_i, (_, row) in enumerate(kpi_df.iterrows(), start=3):
        is_even = (r_i % 2 == 0)
        for c_idx in range(1, total_cols + 1):
            cell = ws.cell(r_i, c_idx)
            val = row.iloc[c_idx - 1]
            cell.value = val
            cell.border = thin_border
            if is_even:
                cell.fill = fill_zebra
            if c_idx <= 3:
                cell.font = body_font
                cell.alignment = align_left if c_idx != 2 else align_center
            else:
                cell.alignment = align_center
                if c_idx in total_col_indices:
                    cell.font = total_font
                else:
                    cell.font = body_font

    # TOTAL Row
    last_r = 3 + len(kpi_df)
    ws.merge_cells(start_row=last_r, start_column=1, end_row=last_r, end_column=3)
    c_tot = ws.cell(last_r, 1, value="TOTAL")
    c_tot.font = total_font
    c_tot.alignment = align_center
    for c in range(1, 4):
        ws.cell(last_r, c).fill = fill_total
        ws.cell(last_r, c).border = thin_border

    for c in range(4, total_cols + 1):
        col_let = get_column_letter(c)
        cell = ws.cell(last_r, c, value=f"=SUM({col_let}3:{col_let}{last_r - 1})")
        cell.font = total_font
        cell.fill = fill_total
        cell.alignment = align_center
        cell.border = thin_border

    return ws
