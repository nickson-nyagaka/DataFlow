"""DATAFLOW Visualisation Framework.

Power BI-inspired, responsive chart rendering components and styling engine.
Strictly adheres to Master Brief §11 and Decisions D-040/D-041 (Pure Presentation).
"""

from __future__ import annotations

from .charts import (
    create_bullet_chart,
    create_cascade_funnel,
    create_grouped_bar,
    create_lollipop_chart,
    create_population_pyramid,
    create_regional_heatmap,
    create_treemap,
    create_waterfall_chart,
)
from .theme import (
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_DARK_TEXT,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    HEIGHT_BULLET,
    HEIGHT_FUNNEL,
    HEIGHT_HEATMAP,
    HEIGHT_LOLLIPOP,
    HEIGHT_PYRAMID,
    HEIGHT_SPARKLINE,
    HEIGHT_STANDARD,
    HEIGHT_TREEMAP,
    apply_chart_theme,
)

__all__ = [
    "COLOR_AMBER",
    "COLOR_BLUE",
    "COLOR_DARK_TEXT",
    "COLOR_GREEN",
    "COLOR_MUTED",
    "COLOR_PURPLE",
    "COLOR_RED",
    "COLOR_TEAL",
    "HEIGHT_BULLET",
    "HEIGHT_FUNNEL",
    "HEIGHT_HEATMAP",
    "HEIGHT_LOLLIPOP",
    "HEIGHT_PYRAMID",
    "HEIGHT_SPARKLINE",
    "HEIGHT_STANDARD",
    "HEIGHT_TREEMAP",
    "apply_chart_theme",
    "create_bullet_chart",
    "create_cascade_funnel",
    "create_grouped_bar",
    "create_lollipop_chart",
    "create_population_pyramid",
    "create_regional_heatmap",
    "create_treemap",
    "create_waterfall_chart",
]
