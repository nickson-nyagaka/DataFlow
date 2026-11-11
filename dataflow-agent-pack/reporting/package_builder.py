"""Reporting package builder assembling multi-tab workbooks and ZIP packages."""

from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from reporting.cleaned_data_exporter import export_dataframe_sheet
from reporting.dqa_exporter import export_dqa_exceptions_sheet
from reporting.excel_exporter import export_age_sex_disaggregation_sheet, export_summary_sheet
from reporting.summary_builder import build_export_summary
from reporting.template_manager import ExcelTemplateConfig, get_template_manager


def export_run_metadata_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    population: str,
    period_mode: str,
    input_file_hash: str = "N/A",
    config_hash: str = "N/A",
    mask_identifiers: bool = False,
    provisional_indicators: list[str] | None = None,
    compat_state: dict[str, Any] | None = None,
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """Renders the Run Metadata sheet with audit trails and confidentiality notice (D-031)."""
    if config is None:
        config = get_template_manager()

    if sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
    else:
        ws = workbook.create_sheet(title=sheet_name)

    header_font = Font(name=config.fonts.header, size=config.fonts.size, bold=True)
    body_font = Font(name=config.fonts.body, size=config.fonts.size, bold=False)
    bold_body_font = Font(name=config.fonts.body, size=config.fonts.size, bold=True)
    thin_side = Side(style="thin", color="000000")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    notice_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = True
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 70

    # Headers
    ws.cell(row=1, column=1, value="Audit Parameter").font = header_font
    ws.cell(row=1, column=1).fill = header_fill
    ws.cell(row=1, column=1).border = thin_border

    ws.cell(row=1, column=2, value="System Value").font = header_font
    ws.cell(row=1, column=2).fill = header_fill
    ws.cell(row=1, column=2).border = thin_border
    ws.row_dimensions[1].height = 24

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    prov_str = (
        ", ".join(provisional_indicators)
        if provisional_indicators
        else "None (All indicators verified)"
    )
    compat_str = (
        ", ".join(f"{k}={v}" for k, v in compat_state.items())
        if compat_state
        else "Standard Production (Legacy switches OFF)"
    )

    metadata_items = [
        ("Application Version", "DATAFLOW v1.0.0"),
        ("Execution Timestamp", timestamp),
        ("Target Population", population.upper()),
        ("Reporting Period", period_mode.upper()),
        ("Source Input File SHA-256", input_file_hash),
        ("Effective Configuration SHA-256", config_hash),
        (
            "Identifier Masking Applied",
            "True"
            if mask_identifiers
            else "False (Full identifiers included for clinical follow-up)",
        ),
        ("Provisional Indicators", prov_str),
        ("Compatibility Engine State", compat_str),
    ]

    r_idx = 2
    for param, val in metadata_items:
        ws.row_dimensions[r_idx].height = 20
        c1 = ws.cell(row=r_idx, column=1, value=param)
        c1.font = bold_body_font
        c1.border = thin_border

        c2 = ws.cell(row=r_idx, column=2, value=str(val))
        c2.font = body_font
        c2.border = thin_border
        r_idx += 1

    # Prominent Confidentiality Notice per D-031
    ws.row_dimensions[r_idx].height = 10
    r_idx += 1

    ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx + 1, end_column=2)
    notice_text = (
        "CONFIDENTIAL MEDICAL INFORMATION: This report contains sensitive HIV Key Population cohort data. "
        "UICs and CCC numbers are preserved strictly for authorized Sub-Recipient clinical follow-up and linkage to care. "
        "Unauthorized redistribution is strictly prohibited under national data protection regulations."
    )
    notice_cell = ws.cell(row=r_idx, column=1, value=notice_text)
    notice_cell.font = Font(name=config.fonts.body, size=10, bold=True, color="C00000")
    notice_cell.fill = notice_fill
    notice_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for r in range(r_idx, r_idx + 2):
        for c in range(1, 3):
            ws.cell(row=r, column=c).border = thin_border
            ws.cell(row=r, column=c).fill = notice_fill

    return ws


def export_cleaning_log_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    cleaning_audit_df: pd.DataFrame | None = None,
    config: ExcelTemplateConfig | None = None,
) -> openpyxl.worksheet.worksheet.Worksheet:
    """Renders the Cleaning Log audit sheet."""
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

    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = True
    ws.row_dimensions[1].height = 24

    cols = ["Rule ID", "Description", "Columns Affected", "Records Affected", "Status"]
    col_widths = {1: 16, 2: 40, 3: 28, 4: 18, 5: 14}

    for c_idx, col in enumerate(cols, start=1):
        c = ws.cell(row=1, column=c_idx, value=col)
        c.font = header_font
        c.fill = header_fill
        c.border = thin_border
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = col_widths.get(
            c_idx, 20
        )

    if cleaning_audit_df is None or cleaning_audit_df.empty:
        ws.cell(row=2, column=1, value="CLN-000").font = body_font
        ws.cell(
            row=2,
            column=2,
            value="Standard ingestion cleaning (whitespace trim, case normalisation)",
        ).font = body_font
        ws.cell(row=2, column=3, value="All demographic columns").font = body_font
        ws.cell(row=2, column=4, value="All rows").font = body_font
        ws.cell(row=2, column=5, value="APPLIED").font = body_font
        for c in range(1, 6):
            ws.cell(row=2, column=c).border = thin_border
        return ws

    for r_idx, (_, row) in enumerate(cleaning_audit_df.iterrows(), start=2):
        ws.row_dimensions[r_idx].height = 18
        for c_idx, col in enumerate(cols, start=1):
            val = row.get(col.lower().replace(" ", "_"), row.get(col, ""))
            c = ws.cell(row=r_idx, column=c_idx, value=str(val))
            c.font = body_font
            c.border = thin_border
            c.alignment = Alignment(
                horizontal="center" if c_idx in [1, 4, 5] else "left", vertical="center"
            )

    return ws


def build_reporting_package(
    cleaned_register: pd.DataFrame,
    cleaned_kplhiv: pd.DataFrame,
    population: str,
    period_mode: str = "SEM",
    dqa_exceptions_df: pd.DataFrame | None = None,
    cleaning_audit_df: pd.DataFrame | None = None,
    output_dir: Path | str = "runtime/exports",
    mask_identifiers: bool = False,
    input_file_hash: str = "N/A",
    config_hash: str = "N/A",
    compat_state: dict[str, Any] | None = None,
    provisional_indicators: list[str] | None = None,
) -> dict[str, Path]:
    """
    Builds both the master multi-tab Excel workbook and the modular ZIP package (D-033).

    Returns a dict with paths to:
    - 'master_workbook': Path to master all-in-one .xlsx
    - 'zip_package': Path to .zip package containing modular workbooks
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manager = get_template_manager()
    layout = manager.get_layout_for(population, period_mode)
    sheet_name = manager.get_sheet_name_for(population, period_mode)

    # 1. Build summary DataFrame
    summary_df = build_export_summary(
        cleaned_register=cleaned_register,
        cleaned_kplhiv=cleaned_kplhiv,
        population=population,
        period_mode=period_mode,
        layout_spec=layout,
    )

    # 2. Build Master Multi-Tab Workbook
    master_wb = openpyxl.Workbook()
    default_sheet = master_wb.active
    if default_sheet is not None:
        master_wb.remove(default_sheet)

    # Tab 1: Summary
    export_summary_sheet(master_wb, sheet_name, summary_df, layout, config=manager)

    # Tab 2: Cleaned Register
    export_dataframe_sheet(
        master_wb,
        "Cleaned Register",
        cleaned_register,
        mask_identifiers=mask_identifiers,
        config=manager,
    )

    # Tab 3: Cleaned KPLHIV
    export_dataframe_sheet(
        master_wb,
        "Cleaned KPLHIV",
        cleaned_kplhiv,
        mask_identifiers=mask_identifiers,
        config=manager,
    )

    # Tab 4: DQA Exceptions
    export_dqa_exceptions_sheet(
        master_wb,
        "DQA Exceptions",
        exceptions_df=dqa_exceptions_df,
        config=manager,
    )

    # Tab 5: Run Metadata
    export_run_metadata_sheet(
        master_wb,
        "Run Metadata",
        population=population,
        period_mode=period_mode,
        input_file_hash=input_file_hash,
        config_hash=config_hash,
        mask_identifiers=mask_identifiers,
        provisional_indicators=provisional_indicators,
        compat_state=compat_state,
        config=manager,
    )

    # Tab 6: Cleaning Log
    export_cleaning_log_sheet(
        master_wb,
        "Cleaning Log",
        cleaning_audit_df=cleaning_audit_df,
        config=manager,
    )

    master_path = out_dir / f"DATAFLOW_Master_{population.upper()}_{period_mode.upper()}.xlsx"
    master_wb.save(master_path)

    # 3. Build Modular Workbooks for ZIP Package
    pop_str = population.upper()
    period_str = period_mode.upper()

    summary_only_path = out_dir / f"01_Summary_{pop_str}_{period_str}.xlsx"
    summary_wb = openpyxl.Workbook()
    if summary_wb.active is not None:
        summary_wb.remove(summary_wb.active)
    export_summary_sheet(summary_wb, sheet_name, summary_df, layout, config=manager)
    summary_wb.save(summary_only_path)

    cleaned_data_path = out_dir / f"02_Cleaned_Data_{pop_str}.xlsx"
    cleaned_wb = openpyxl.Workbook()
    if cleaned_wb.active is not None:
        cleaned_wb.remove(cleaned_wb.active)
    export_dataframe_sheet(
        cleaned_wb,
        "Cleaned Register",
        cleaned_register,
        mask_identifiers=mask_identifiers,
        config=manager,
    )
    export_dataframe_sheet(
        cleaned_wb,
        "Cleaned KPLHIV",
        cleaned_kplhiv,
        mask_identifiers=mask_identifiers,
        config=manager,
    )
    cleaned_wb.save(cleaned_data_path)

    dqa_path = out_dir / f"03_DQA_Exceptions_{pop_str}.xlsx"
    dqa_wb = openpyxl.Workbook()
    if dqa_wb.active is not None:
        dqa_wb.remove(dqa_wb.active)
    export_dqa_exceptions_sheet(
        dqa_wb, "DQA Exceptions", exceptions_df=dqa_exceptions_df, config=manager
    )
    dqa_wb.save(dqa_path)

    # Standalone Age x Sex Disaggregation workbook per D-039
    disagg_path: Path | None = None
    if period_str in ["SEM", "Q1", "Q2"]:
        disagg_path = out_dir / f"04_Age_Sex_Disaggregation_{pop_str}.xlsx"
        disagg_wb = openpyxl.Workbook()
        if disagg_wb.active is not None:
            disagg_wb.remove(disagg_wb.active)
        export_age_sex_disaggregation_sheet(
            disagg_wb, "Age_Sex_Disaggregation", cleaned_register, config=manager
        )
        disagg_wb.save(disagg_path)

    # 4. Assemble ZIP Package
    zip_path = out_dir / f"DATAFLOW_Package_{pop_str}_{period_str}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(master_path, arcname=master_path.name)
        zf.write(summary_only_path, arcname=summary_only_path.name)
        zf.write(cleaned_data_path, arcname=cleaned_data_path.name)
        zf.write(dqa_path, arcname=dqa_path.name)
        if disagg_path and disagg_path.exists():
            zf.write(disagg_path, arcname=disagg_path.name)

    return {
        "master_workbook": master_path,
        "summary_workbook": summary_only_path,
        "cleaned_data_workbook": cleaned_data_path,
        "dqa_workbook": dqa_path,
        "disaggregation_workbook": disagg_path if disagg_path else master_path,
        "zip_package": zip_path,
    }
