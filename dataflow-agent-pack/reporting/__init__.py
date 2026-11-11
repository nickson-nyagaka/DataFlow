"""DATAFLOW reporting package — Excel exporters, template manager, and package builders."""

from __future__ import annotations

from reporting.cleaned_data_exporter import export_cleaned_data_workbook
from reporting.dqa_exporter import export_dqa_exceptions_workbook
from reporting.excel_exporter import export_summary_sheet, export_summary_workbook
from reporting.package_builder import build_reporting_package
from reporting.summary_builder import build_export_summary
from reporting.template_manager import (
    ExcelTemplateConfig,
    LayoutBlock,
    LayoutSpec,
    get_template_manager,
)
from reporting.workbook_validator import validate_summary_workbook

__all__ = [
    "ExcelTemplateConfig",
    "LayoutBlock",
    "LayoutSpec",
    "build_export_summary",
    "build_reporting_package",
    "export_cleaned_data_workbook",
    "export_dqa_exceptions_workbook",
    "export_summary_sheet",
    "export_summary_workbook",
    "get_template_manager",
    "validate_summary_workbook",
]
