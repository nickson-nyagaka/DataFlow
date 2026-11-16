"""DATAFLOW Reusable Chart Builders (Plotly 7.1.0 Engine).

Implements Master Brief §11 and Phase Plan objectives:
- Power BI-inspired visual styling with clean axes, tooltips, and legends.
- Dimension stabilization (fixed heights, auto-scaling width).
- Strict adherence to typology rules for demographic and clinical representations.
"""

from __future__ import annotations

import plotly.graph_objects as go

from .theme import (
    CASCADE_COLORS,
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_DARK_TEXT,
    COLOR_GREEN,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    HEIGHT_BULLET,
    HEIGHT_FUNNEL,
    HEIGHT_HEATMAP,
    HEIGHT_LOLLIPOP,
    HEIGHT_PYRAMID,
    HEIGHT_STANDARD,
    HEIGHT_TREEMAP,
    apply_chart_theme,
)


def create_bullet_chart(
    title: str,
    actual: float,
    target: float,
    max_val: float = 100.0,
    unit: str = "%",
    numerator: int | None = None,
    denominator: int | None = None,
) -> go.Figure:
    """Creates a high-impact executive performance bullet chart.

    Displays actual achievement bar, target marker line, and achievement ratio.
    """
    if actual >= target:
        bar_color = COLOR_GREEN
        status_label = "On Track"
    elif actual >= target - 10.0:
        bar_color = COLOR_AMBER
        status_label = "Needs Attention"
    else:
        bar_color = COLOR_RED
        status_label = "Below Target"

    context_str = ""
    if numerator is not None and denominator is not None and denominator > 0:
        context_str = f" ({numerator:,} / {denominator:,})"

    fig = go.Figure()

    # Background benchmark track
    fig.add_trace(
        go.Bar(
            y=[title],
            x=[max_val],
            orientation="h",
            marker={"color": "#F0F3F6"},
            hoverinfo="none",
            showlegend=False,
        )
    )

    # Actual performance bar
    fig.add_trace(
        go.Bar(
            y=[title],
            x=[min(actual, max_val)],
            orientation="h",
            marker={"color": bar_color},
            name="Actual",
            hovertemplate=(
                f"<b>{title}</b><br>"
                f"Actual: {actual:.1f}{unit}{context_str}<br>"
                f"Target: {target:.1f}{unit}<br>"
                f"Status: {status_label}<extra></extra>"
            ),
            text=[f"  {actual:.1f}{unit}{context_str}"],
            textposition="inside" if actual > 25 else "outside",
            textfont={"size": 11, "color": "#FFFFFF" if actual > 25 else COLOR_DARK_TEXT},
            showlegend=False,
        )
    )

    # Target marker line
    fig.add_shape(
        type="line",
        x0=target,
        x1=target,
        y0=-0.4,
        y1=0.4,
        line={"color": "#2C3E50", "width": 3, "dash": "dash"},
    )

    # Subtitle annotation
    fig.add_annotation(
        x=target,
        y=0.45,
        text=f"Target: {target:.1f}{unit}",
        showarrow=False,
        font={"size": 10, "color": "#7F8C8D"},
        xanchor="center",
    )

    fig.update_xaxes(range=[0, max(max_val, actual * 1.05)], title_text=f"Achievement ({unit})")
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(barmode="overlay")

    return apply_chart_theme(fig, height=HEIGHT_BULLET, title=f"{title} — {status_label}")


def create_cascade_funnel(
    stages: list[str],
    values: list[int],
    title: str,
    colors: list[str] | None = None,
) -> go.Figure:
    """Creates an interactive sequential cascade funnel chart for genuine flows (e.g. HTS, ART)."""
    if not colors:
        colors = CASCADE_COLORS[: len(stages)]

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value",
            texttemplate="%{value:,}",
            textposition="inside",
            marker={"color": colors},
            hovertemplate="<b>%{y}</b><br>Clients: %{x:,}<extra></extra>",
            connector={"line": {"color": "#BDC3C7", "dash": "dot", "width": 1}},
        )
    )

    return apply_chart_theme(fig, height=HEIGHT_FUNNEL, title=title, margin_left=80)


def create_waterfall_chart(
    stages: list[str],
    values: list[int],
    title: str,
    annotations_text: list[str] | None = None,
) -> go.Figure:
    """Creates a vertical Waterfall chart with connector lines and prominent stage values."""
    if not annotations_text:
        annotations_text = [f"<b>{v:,}</b>" for v in values]

    max_v = max(values) if values else 100
    fig = go.Figure(
        go.Waterfall(
            name=title,
            orientation="v",
            measure=["absolute"] * len(stages),
            x=stages,
            y=values,
            text=annotations_text,
            textposition="outside",
            cliponaxis=False,
            connector={"line": {"color": "#7F8C8D", "width": 2, "dash": "solid"}},
            totals={"marker": {"color": COLOR_BLUE}},
            hovertemplate="<b>%{x}</b><br>Clients: %{y:,}<extra></extra>",
        )
    )

    fig.update_yaxes(range=[0, max_v * 1.25], title_text="Clients")
    return apply_chart_theme(fig, height=HEIGHT_FUNNEL, title=title)


def create_regional_heatmap(
    x_labels: list[str],
    y_labels: list[str],
    z_data: list[list[float]],
    title: str,
    z_unit: str = "%",
) -> go.Figure:
    """Creates a clean regional / Sub-Recipient performance heatmap."""
    text_data = [[f"{val:.1f}{z_unit}" if val > 0 else "0.0%" for val in row] for row in z_data]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            text=text_data,
            texttemplate="%{text}",
            colorscale="Greens",
            showscale=True,
            colorbar={"title": z_unit, "thickness": 12, "len": 0.8},
            hovertemplate="<b>%{y}</b> | %{x}<br>Coverage: %{z:.1f}" + z_unit + "<extra></extra>",
        )
    )

    return apply_chart_theme(fig, height=HEIGHT_HEATMAP, title=title, margin_left=90)


def create_lollipop_chart(
    categories: list[str],
    values: list[float],
    title: str,
    x_label: str = "Coverage (%)",
    benchmark_line: float | None = None,
) -> go.Figure:
    """Creates a horizontal lollipop / ranked chart for comparing Sub-Recipients or Counties."""
    fig = go.Figure()

    # Stem lines
    for cat, val in zip(categories, values, strict=False):
        fig.add_trace(
            go.Scatter(
                x=[0, val],
                y=[cat, cat],
                mode="lines",
                line={"color": "#BDC3C7", "width": 2},
                hoverinfo="none",
                showlegend=False,
            )
        )

    # Bubble heads
    fig.add_trace(
        go.Scatter(
            x=values,
            y=categories,
            mode="markers+text",
            marker={"color": COLOR_BLUE, "size": 14, "line": {"color": "#1A5276", "width": 1.5}},
            text=[f"{v:.1f}%" if "%" in x_label else f"{int(v):,}" for v in values],
            textposition="middle right",
            textfont={"size": 11, "color": COLOR_DARK_TEXT},
            hovertemplate="<b>%{y}</b><br>" + x_label + ": %{x}<extra></extra>",
            showlegend=False,
        )
    )

    # Optional benchmark line
    if benchmark_line is not None:
        fig.add_shape(
            type="line",
            x0=benchmark_line,
            x1=benchmark_line,
            y0=-0.5,
            y1=len(categories) - 0.5,
            line={"color": COLOR_RED, "width": 2, "dash": "dash"},
        )
        fig.add_annotation(
            x=benchmark_line,
            y=len(categories) - 0.5,
            text=f"Benchmark: {benchmark_line:.0f}%",
            showarrow=False,
            font={"size": 10, "color": COLOR_RED},
            xanchor="left",
        )

    max_x = max(values) if values else 100
    fig.update_xaxes(range=[0, max(max_x * 1.25, 105)], title_text=x_label)
    fig.update_yaxes(autorange="reversed")

    return apply_chart_theme(fig, height=HEIGHT_LOLLIPOP, title=title, margin_left=110)


def create_population_pyramid(
    age_groups: list[str],
    male_counts: list[int],
    female_counts: list[int],
    population: str,
    title: str = "Cohort Demographic Distribution",
) -> go.Figure:
    """Renders demographic age/sex distribution with strict adherence to typology business rules.

    - FSW: Female-only horizontal bar chart (Male column prohibited).
    - MSM: Male-only horizontal bar chart (Female column prohibited).
    - PWID, TG, VP: Bilateral population pyramid (Male vs Female).
    """
    pop_upper = population.strip().upper()
    fig = go.Figure()

    if pop_upper == "FSW":
        # Female only per typology rules
        fig.add_trace(
            go.Bar(
                y=age_groups,
                x=female_counts,
                orientation="h",
                marker={"color": COLOR_PURPLE},
                name="Female",
                hovertemplate="Age Group: %{y}<br>Female Clients: %{x:,}<extra></extra>",
                text=[f"{c:,}" for c in female_counts],
                textposition="inside",
            )
        )
        fig.update_xaxes(title_text="Female Clients (FSW Typology Rule)")

    elif pop_upper == "MSM":
        # Male only per typology rules
        fig.add_trace(
            go.Bar(
                y=age_groups,
                x=male_counts,
                orientation="h",
                marker={"color": COLOR_BLUE},
                name="Male",
                hovertemplate="Age Group: %{y}<br>Male Clients: %{x:,}<extra></extra>",
                text=[f"{c:,}" for c in male_counts],
                textposition="inside",
            )
        )
        fig.update_xaxes(title_text="Male Clients (MSM Typology Rule)")

    else:
        # Dual bilateral pyramid for PWID, TG, VP
        # Male on left (negative values for visualization, positive in hover)
        neg_males = [-c for c in male_counts]
        fig.add_trace(
            go.Bar(
                y=age_groups,
                x=neg_males,
                orientation="h",
                marker={"color": COLOR_BLUE},
                name="Male",
                hovertemplate="Age Group: %{y}<br>Male Clients: %{customdata:,}<extra></extra>",
                customdata=male_counts,
                text=[f"{c:,}" if c > 0 else "" for c in male_counts],
                textposition="auto",
            )
        )

        fig.add_trace(
            go.Bar(
                y=age_groups,
                x=female_counts,
                orientation="h",
                marker={"color": COLOR_PURPLE},
                name="Female",
                hovertemplate="Age Group: %{y}<br>Female Clients: %{x:,}<extra></extra>",
                text=[f"{c:,}" if c > 0 else "" for c in female_counts],
                textposition="auto",
            )
        )

        # Mirror axis symmetrically
        max_c = max(max(male_counts, default=0), max(female_counts, default=0), 10)
        tick_vals = [-max_c, -int(max_c / 2), 0, int(max_c / 2), max_c]
        tick_text = [f"{abs(v):,}" for v in tick_vals]

        fig.update_xaxes(
            tickvals=tick_vals,
            ticktext=tick_text,
            title_text="Male ◄ | ► Female Clients",
        )

    fig.update_layout(barmode="relative")
    return apply_chart_theme(fig, height=HEIGHT_PYRAMID, title=title, show_legend=True, margin_left=80)


def create_treemap(
    labels: list[str],
    parents: list[str],
    values: list[int],
    title: str,
) -> go.Figure:
    """Creates a hierarchical treemap for multi-dimensional commodity or cohort breakdown."""
    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            textinfo="label+value",
            marker={"colorscale": "Blues"},
            hovertemplate="<b>%{label}</b><br>Total Units: %{value:,}<extra></extra>",
        )
    )

    return apply_chart_theme(fig, height=HEIGHT_TREEMAP, title=title)


def create_grouped_bar(
    categories: list[str],
    series_dict: dict[str, list[int]],
    title: str,
    y_label: str = "Clients",
) -> go.Figure:
    """Creates grouped horizontal or vertical bars with discrete series colors."""
    palette = [COLOR_BLUE, COLOR_AMBER, COLOR_GREEN, COLOR_PURPLE, COLOR_TEAL]
    fig = go.Figure()

    for idx, (series_name, vals) in enumerate(series_dict.items()):
        color = palette[idx % len(palette)]
        fig.add_trace(
            go.Bar(
                x=categories,
                y=vals,
                name=series_name,
                marker={"color": color},
                hovertemplate=f"<b>%{{x}}</b><br>{series_name}: %{{y:,}}<extra></extra>",
                text=[f"{v:,}" if v > 0 else "" for v in vals],
                textposition="inside",
            )
        )

    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text=y_label)

    return apply_chart_theme(fig, height=HEIGHT_STANDARD, title=title, show_legend=True)
