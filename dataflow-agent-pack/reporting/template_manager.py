"""Template manager for Excel report generation, driven by YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LayoutBlock:
    """Represents a grouped block of columns in the Excel header structure."""

    group: str
    subheaders: list[str]
    columns: list[str]

    def __post_init__(self) -> None:
        if len(self.subheaders) != len(self.columns):
            raise ValueError(
                f"Block '{self.group}' has mismatched subheaders ({len(self.subheaders)}) "
                f"and columns ({len(self.columns)})"
            )


@dataclass(frozen=True)
class LayoutSpec:
    """Complete layout specification for a specific population and period mode."""

    name: str
    blocks: list[LayoutBlock]

    @property
    def all_columns(self) -> list[str]:
        cols: list[str] = []
        for b in self.blocks:
            cols.extend(b.columns)
        return cols

    @property
    def all_subheaders(self) -> list[str]:
        subs: list[str] = []
        for b in self.blocks:
            subs.extend(b.subheaders)
        return subs

    @property
    def total_columns(self) -> int:
        return len(self.all_columns)


@dataclass(frozen=True)
class FontSpec:
    header: str = "Cascadia Code"
    body: str = "Candara"
    size: int = 11


@dataclass(frozen=True)
class FillSpec:
    subheader: str = "FF7D81"
    total: str = "6BD669"
    fallback: str = "FF7D81"


@dataclass(frozen=True)
class DimensionSpec:
    col_width_keys: int = 22
    col_width_data: int = 14
    row_height_group: int = 22
    row_height_sub: int = 30


@dataclass
class ExcelTemplateConfig:
    fonts: FontSpec = field(default_factory=FontSpec)
    fills: FillSpec = field(default_factory=FillSpec)
    group_colors: dict[str, str] = field(default_factory=dict)
    dimensions: DimensionSpec = field(default_factory=DimensionSpec)
    layouts: dict[str, LayoutSpec] = field(default_factory=dict)

    def get_group_fill(self, group_name: str) -> str:
        """Returns the hex fill color for a group header block, or fallback if unmapped."""
        clean = group_name.strip().upper()
        # Direct lookup or stripped lookup
        for k, v in self.group_colors.items():
            if k.strip().upper() == clean:
                return v
        return self.fills.fallback

    def get_layout(self, layout_name: str) -> LayoutSpec:
        """Retrieves layout specification by name."""
        if layout_name not in self.layouts:
            raise KeyError(
                f"Unknown layout '{layout_name}'. Available: {list(self.layouts.keys())}"
            )
        return self.layouts[layout_name]

    def get_layout_for(self, population: str, period_mode: str) -> LayoutSpec:
        """Resolves the appropriate layout specification for given population and period mode."""
        pop = population.strip().upper()
        mode = period_mode.strip().upper()

        if mode == "Q1":
            layout_key = "q1_pwid" if pop == "PWID" else "q1_standard"
        else:
            layout_key = "semester_pwid" if pop == "PWID" else "semester_standard"

        return self.get_layout(layout_key)

    def get_sheet_name_for(self, population: str, period_mode: str) -> str:
        """Resolves target summary worksheet name matching legacy template naming."""
        pop = population.strip().upper()
        mode = period_mode.strip().upper()

        if pop == "PWID":
            return "PWID_Summary"
        if mode == "Q1":
            return "KP_Summary"
        return "Summary"


def load_template_config(config_path: Path | str | None = None) -> ExcelTemplateConfig:
    """Loads and validates the Excel templates configuration from YAML."""
    if config_path is None:
        p = Path(__file__).resolve().parent.parent / "config" / "reporting" / "excel_templates.yaml"
    else:
        p = Path(config_path)

    if not p.is_file():
        raise FileNotFoundError(f"Excel template configuration not found at: {p}")

    with open(p, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    raw_fonts = data.get("fonts", {})
    fonts = FontSpec(
        header=str(raw_fonts.get("header", "Cascadia Code")),
        body=str(raw_fonts.get("body", "Candara")),
        size=int(raw_fonts.get("size", 11)),
    )

    raw_fills = data.get("fills", {})
    fills = FillSpec(
        subheader=str(raw_fills.get("subheader", "FF7D81")),
        total=str(raw_fills.get("total", "6BD669")),
        fallback=str(raw_fills.get("fallback", "FF7D81")),
    )

    group_colors = {str(k): str(v) for k, v in data.get("group_colors", {}).items()}

    raw_dims = data.get("dimensions", {})
    dimensions = DimensionSpec(
        col_width_keys=int(raw_dims.get("col_width_keys", 22)),
        col_width_data=int(raw_dims.get("col_width_data", 14)),
        row_height_group=int(raw_dims.get("row_height_group", 22)),
        row_height_sub=int(raw_dims.get("row_height_sub", 30)),
    )

    raw_layouts = data.get("layouts", {})
    layouts: dict[str, LayoutSpec] = {}
    for lname, ldata in raw_layouts.items():
        blocks: list[LayoutBlock] = []
        for b in ldata.get("blocks", []):
            blocks.append(
                LayoutBlock(
                    group=str(b.get("group", "")),
                    subheaders=[str(s) for s in b.get("subheaders", [])],
                    columns=[str(c) for c in b.get("columns", [])],
                )
            )
        layouts[lname] = LayoutSpec(name=lname, blocks=blocks)

    return ExcelTemplateConfig(
        fonts=fonts,
        fills=fills,
        group_colors=group_colors,
        dimensions=dimensions,
        layouts=layouts,
    )


_GLOBAL_TEMPLATE_MANAGER: ExcelTemplateConfig | None = None


def get_template_manager(config_path: Path | str | None = None) -> ExcelTemplateConfig:
    """Returns singleton template manager instance."""
    global _GLOBAL_TEMPLATE_MANAGER
    if _GLOBAL_TEMPLATE_MANAGER is None or config_path is not None:
        cfg = load_template_config(config_path)
        if config_path is None:
            _GLOBAL_TEMPLATE_MANAGER = cfg
        return cfg
    return _GLOBAL_TEMPLATE_MANAGER
