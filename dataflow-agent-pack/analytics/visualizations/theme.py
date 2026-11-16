"""DATAFLOW Visualisation Theme and Standard Layout Engine.

Provides consistent dimensions, responsive container rules, and Power BI-inspired
clean typography and palette styling for Plotly charts.
"""

from __future__ import annotations

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# COLOR PALETTE (Global Fund & Power BI Inspired)
# ---------------------------------------------------------------------------
COLOR_GREEN = "#00B050"       # Primary Global Fund Green (Positive / On Track)
COLOR_BLUE = "#1F77B4"        # Testing / HTS Brand Blue
COLOR_TEAL = "#00A8B5"        # Prevention / PrEP Teal
COLOR_PURPLE = "#7B2CBF"      # Treatment / ART Purple
COLOR_AMBER = "#F39C12"       # Warning / Needs Attention
COLOR_RED = "#E74C3C"         # Critical / Below Target / Alert
COLOR_MUTED = "#95A5A6"       # Inactive / Missing / Neutral
COLOR_DARK_TEXT = "#2C3E50"   # High contrast header and axis label text
COLOR_BG_LIGHT = "#FFFFFF"    # Pure white card canvas background
COLOR_GRID = "#EBF0F5"        # Subtle non-intrusive grid line

# Semantic palette for cascades
CASCADE_COLORS = [
    "#1F77B4",  # Stage 1: Blue
    "#00A8B5",  # Stage 2: Teal
    "#00B050",  # Stage 3: Green
    "#7B2CBF",  # Stage 4: Purple
    "#E67E22",  # Stage 5: Orange
]

# ---------------------------------------------------------------------------
# STANDARD CHART HEIGHTS (Enforces dimension stability across scroll/render)
# ---------------------------------------------------------------------------
HEIGHT_SPARKLINE = 110
HEIGHT_BULLET = 160
HEIGHT_GAUGE = 220
HEIGHT_STANDARD = 350
HEIGHT_FUNNEL = 360
HEIGHT_LOLLIPOP = 360
HEIGHT_HEATMAP = 400
HEIGHT_PYRAMID = 400
HEIGHT_TREEMAP = 360


def apply_chart_theme(
    fig: go.Figure,
    height: int = HEIGHT_STANDARD,
    title: str | None = None,
    show_legend: bool = False,
    margin_top: int = 40,
    margin_bottom: int = 40,
    margin_left: int = 40,
    margin_right: int = 30,
) -> go.Figure:
    """Applies standardized Power BI-style formatting, fixed height, and responsive settings.

    Fixes the root causes of unexpected chart resizing during viewport scrolling:
    - Fixed explicit height in pixels prevents auto-size recalculation jumps.
    - Autosize enabled for responsive width scaling to container.
    - Non-intrusive margins with zero outer padding inflation.
    - Clean typography matching Streamlit's font stack.
    """
    layout_update: dict[str, object] = {
        "height": height,
        "autosize": True,
        "paper_bgcolor": COLOR_BG_LIGHT,
        "plot_bgcolor": COLOR_BG_LIGHT,
        "font": {
            "family": "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
            "size": 12,
            "color": COLOR_DARK_TEXT,
        },
        "margin": {
            "t": margin_top if title else 25,
            "b": margin_bottom,
            "l": margin_left,
            "r": margin_right,
            "pad": 4,
        },
        "showlegend": show_legend,
        "hoverlabel": {
            "bgcolor": "#2C3E50",
            "font": {"color": "#FFFFFF", "size": 12},
            "bordercolor": "#2C3E50",
        },
    }

    if title:
        layout_update["title"] = {
            "text": f"<b>{title}</b>",
            "font": {"size": 14, "color": COLOR_DARK_TEXT},
            "x": 0.02,
            "xanchor": "left",
            "y": 0.96,
        }

    fig.update_layout(**layout_update)

    # Standardize axes if present
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=COLOR_GRID,
        zeroline=True,
        zerolinecolor="#BDC3C7",
        tickfont={"size": 11, "color": "#5D6D7E"},
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=COLOR_GRID,
        zeroline=True,
        zerolinecolor="#BDC3C7",
        tickfont={"size": 11, "color": "#5D6D7E"},
    )

    return fig
