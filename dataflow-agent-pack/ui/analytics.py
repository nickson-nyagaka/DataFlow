"""DATAFLOW Analytics Page — Interactive MEL Analysis Workbench.

Primary Audience: Monitoring & Evaluation (M&E) Specialists, Data Analysts, Epidemiologists.
Primary Question: "What exactly is happening, where is it happening, which indicators are affected, and what explains the differences?"

Strictly adheres to Master Brief §11 and Decisions D-040/D-041:
- Pure presentation layer: consumes pre-computed results in PipelineResult and display_analytics.
- STRICT CONSTRAINT: Zero analytical calculations, groupby, or formulas in ui/.
- Adheres strictly to typology-specific age and sex demographic business rules.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

# Ensure project root takes precedence in sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] != _ROOT:
    if _ROOT in sys.path:
        sys.path.remove(_ROOT)
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from analytics.display_summary import (  # noqa: E402
    append_total_row,
    extract_art_cascade,
    extract_clinical_cascade,
    extract_commodities,
    extract_demographic_pyramid,
    extract_hts_cascade,
    extract_prep_cascade,
    style_table_with_total_row,
)
from analytics.visualizations.charts import (  # noqa: E402
    create_cascade_funnel,
    create_grouped_bar,
    create_population_pyramid,
    create_treemap,
    create_waterfall_chart,
)
from core.workflow_manager import WorkflowStage  # noqa: E402
from ui.session import (  # noqa: E402
    advance_workflow_stage,
    get_active_pipeline_result,
    get_current_workflow_stage,
    render_access_guard,
)


# =============================================================================
# PRESENTATION DESIGN SYSTEM (display-only: colours, CSS, layout polish)
# =============================================================================
# Every section is wrapped in a keyed container (st-key-<name>) so the CSS below
# only touches that section. Each section owns an accent palette that is reused
# by its KPI cards and its charts, so cards and charts always match.
_SECTION_ACCENTS: dict[str, list[str]] = {
    "hts_section": ["#3B82F6", "#22C55E", "#EF4444", "#8B5CF6"],
    "prep_section": ["#06B6D4", "#22C55E", "#3B82F6", "#14B8A6", "#8B5CF6", "#F97316"],
    "art_section": ["#6366F1", "#3B82F6", "#14B8A6", "#22C55E"],
    "clin_section": ["#F59E0B", "#EF4444", "#22C55E", "#8B5CF6"],
    "comm_section": ["#0EA5E9", "#EC4899", "#F59E0B", "#10B981", "#8B5CF6", "#EF4444"],
    "demo_section": ["#3B82F6", "#EC4899"],
}

# HTS stage colours (cards, bar chart and badges stay consistent)
_HTS_COLORS = {
    "Tested": "#3B82F6",         # blue
    "Negative": "#22C55E",       # green
    "Positive": "#EF4444",       # red
    "Linked to ART": "#8B5CF6",  # violet
}

_MALE_COLOR = "#3B82F6"
_FEMALE_COLOR = "#EC4899"

_CARD_CSS_TEMPLATE = """
.st-key-__K__ [data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.07);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-left: 6px solid #3B82F6;
    border-radius: 14px;
    padding: 16px 20px 14px 20px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.st-key-__K__ [data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
}
.st-key-__K__ [data-testid="stMetricLabel"] p {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.75;
}
.st-key-__K__ [data-testid="stMetricValue"] {
    font-size: 2.1rem;
    font-weight: 700;
    line-height: 1.15;
}
.st-key-__K__ button[data-baseweb="tab"] { font-weight: 600; }
.st-key-__K__ [data-testid="stPlotlyChart"] {
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 14px;
    padding: 6px;
}
.st-key-__K__ [data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid rgba(128, 128, 128, 0.22);
}
.st-key-__K__ [data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}
"""


def _build_css() -> str:
    """Assemble the scoped stylesheet for every analytics section."""
    parts = ["<style>"]
    for key, accents in _SECTION_ACCENTS.items():
        parts.append(_CARD_CSS_TEMPLATE.replace("__K__", key))
        for i, color in enumerate(accents, start=1):
            parts.append(
                f'.st-key-{key} [data-testid="stHorizontalBlock"] > div:nth-child({i}) '
                f'[data-testid="stMetric"] {{ border-left-color: {color}; }}'
            )
    # Summary tables section (7 & 8)
    parts.append(
        '.st-key-tables_section [data-testid="stDataFrame"] {'
        " border: 1px solid rgba(128,128,128,0.22); border-radius: 12px; overflow: hidden; }"
    )
    # Context badges (shared by every section)
    parts.append(
        """
.dfx-badges { display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 14px 0; }
.dfx-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.35);
}
.dfx-badge.filter {
    background: rgba(245, 158, 11, 0.14);
    border-color: rgba(245, 158, 11, 0.45);
}
"""
    )
    parts.append("</style>")
    return "\n".join(parts)


def _section_container(key: str):
    """Keyed container so the CSS above only touches this section.

    Streamlit < 1.39 does not support container keys; in that case we fall back
    to a plain container (everything still renders, the card styling just does
    not apply).
    """
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


def _badges_html(population: str, period_mode: str | None, filter_tags: list[str]) -> str:
    """Small chip row showing the active cohort, period and filters."""
    chips = [f'<span class="dfx-badge">👥 {html.escape(str(population))}</span>']
    if period_mode:
        chips.append(f'<span class="dfx-badge">🗓️ {html.escape(str(period_mode))}</span>')
    for tag in filter_tags:
        chips.append(f'<span class="dfx-badge filter">🔎 {html.escape(tag)}</span>')
    return f'<div class="dfx-badges">{"".join(chips)}</div>'


def _palette(key: str, n: int) -> list[str]:
    """Section accent colours, cycled to exactly n items."""
    colors = _SECTION_ACCENTS.get(key, ["#3B82F6"])
    return [colors[i % len(colors)] for i in range(n)]


def _fmt_num(v):
    """Thousands-separated number for tables; leaves non-numbers untouched."""
    return f"{v:,}" if isinstance(v, (int, float)) else v


def _polish_figure(fig: go.Figure, height: int = 440) -> go.Figure:
    """Layout-only polish applied on top of a chart built in analytics.visualizations."""
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=70, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=14),
        hoverlabel=dict(font_size=13),
        title_x=0.01,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.20)", zeroline=False)
    return fig


def _style_bar_figure(fig: go.Figure, colors: list[str], height: int = 440, bargap: float = 0.35) -> go.Figure:
    """Colour-coded vertical bars with value labels and clean hover."""
    fig.update_traces(
        selector=dict(type="bar"),
        marker_color=colors,
        marker_line_width=0,
        texttemplate="%{y:,}",
        textposition="outside",
        textfont=dict(size=14),
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
    )
    fig.update_layout(bargap=bargap, showlegend=False)
    fig.update_yaxes(rangemode="tozero", tickformat="d")
    return _polish_figure(fig, height=height)


def _style_funnel_figure(fig: go.Figure, colors: list[str], height: int = 460) -> go.Figure:
    """Gradient-coloured funnel; labels show the count and % of the previous stage."""
    fig.update_traces(
        selector=dict(type="funnel"),
        marker=dict(color=colors),
        textinfo="value+percent previous",
        textfont=dict(size=15, color="white"),
        connector=dict(line=dict(color="rgba(128,128,128,0.35)", width=1)),
        hovertemplate="<b>%{y}</b><br>Clients: %{x:,}<extra></extra>",
    )
    return _polish_figure(fig, height=height)


def _style_treemap_figure(fig: go.Figure, colors: list[str], height: int = 440) -> go.Figure:
    """Coloured, borderless treemap tiles with large readable labels."""
    fig.update_traces(
        selector=dict(type="treemap"),
        marker=dict(colors=colors, line=dict(width=3, color="rgba(0,0,0,0)")),
        textinfo="label+value",
        textfont=dict(size=17),
        pathbar=dict(visible=False),
        root_color="rgba(0,0,0,0)",
        hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>",
    )
    return _polish_figure(fig, height=height)


def _style_pyramid_figure(fig: go.Figure, height: int = 460) -> go.Figure:
    """Blue/pink sex colours, horizontal legend and a tighter bar gap."""
    for trace in fig.data:
        name = str(getattr(trace, "name", "") or "").strip().lower()
        if name.startswith("female") or name == "f":
            trace.marker.color = _FEMALE_COLOR
        elif name.startswith("male") or name == "m":
            trace.marker.color = _MALE_COLOR
    fig.update_layout(
        bargap=0.12,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01),
    )
    return _polish_figure(fig, height=height)


def _hts_breakdown_figure(stages: list[str], values: list[int], title: str) -> go.Figure:
    """Colour-coded bar chart for the HTS 'Complete Indicator Breakdown' tab."""
    colors = [_HTS_COLORS.get(s, "#64748B") for s in stages]
    fig = go.Figure(
        go.Bar(
            x=stages,
            y=values,
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:,}" for v in values],
            textposition="outside",
            textfont=dict(size=15),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Clients: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(title=dict(text=title), showlegend=False, bargap=0.35)
    fig.update_yaxes(title_text="Clients", rangemode="tozero", tickformat=",")
    return _polish_figure(fig, height=440)


def _data_table_expander(data: dict, label: str = "📋 View data as table") -> None:
    """Collapsible table of the exact values behind a chart (display only)."""
    with st.expander(label):
        tbl = pd.DataFrame(
            {"Indicator": list(data.keys()), "Value": list(data.values())}
        ).set_index("Indicator")
        st.dataframe(tbl.style.format(_fmt_num, subset=["Value"]), use_container_width=True)


def render_analytics() -> None:
    st.title("📊 Key Population Analytics")
    st.caption("Monitoring, Evaluation & Learning (MEL) Workbench — Pre-aggregated cascade funnels, demographic disaggregations, and facility tables.")

    # Guard check
    if not render_access_guard("Analytics"):
        return

    # Record analytics viewed in session and advance workflow to unlock Export Reports
    st.session_state["analytics_viewed"] = True
    if get_current_workflow_stage() == WorkflowStage.DASHBOARD_VIEWED:
        advance_workflow_stage(WorkflowStage.ANALYTICS_VIEWED)

    result = get_active_pipeline_result()
    if not result:
        st.warning("No active processed pipeline result found in this session. Please run processing first.")
        return

    # One stylesheet for every section (scoped per section via container keys)
    st.markdown(_build_css(), unsafe_allow_html=True)

    disp = result.display_analytics or {}
    population = result.population
    period_mode = result.period_mode
    geo_matrix = disp.get("geography_matrix", {})
    regions_list = geo_matrix.get("regions", [])
    geo_hierarchy = geo_matrix.get("hierarchy", {})

    # =========================================================================
    # MODULE A: ANALYTICS FILTER BAR
    # =========================================================================
    if "prev_filter_region" not in st.session_state:
        st.session_state["prev_filter_region"] = "All Regions"
    if "prev_filter_county" not in st.session_state:
        st.session_state["prev_filter_county"] = "All Counties"

    with st.container(border=True):
        f_top1, f_top2 = st.columns([5, 1])
        with f_top1:
            st.markdown("#### 🔎 Interactive Geographical & Indicator Filter Bar")
        with f_top2:
            if st.button("Reset ↺", use_container_width=True, help="Reset all filters to national view"):
                st.session_state["sel_region"] = "All Regions"
                st.session_state["sel_county"] = "All Counties"
                st.session_state["sel_sr"] = "All Sub-Recipients"
                st.session_state["sel_category"] = "All Indicators"
                st.session_state["prev_filter_region"] = "All Regions"
                st.session_state["prev_filter_county"] = "All Counties"
                st.rerun()

        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        with f_col1:
            region_options = ["All Regions"] + regions_list
            selected_region = st.selectbox("Region", options=region_options, key="sel_region")

        # When Region changes, cascade reset to child filters
        if selected_region != st.session_state["prev_filter_region"]:
            st.session_state["prev_filter_region"] = selected_region
            st.session_state["sel_county"] = "All Counties"
            st.session_state["sel_sr"] = "All Sub-Recipients"

        with f_col2:
            if selected_region != "All Regions" and selected_region in geo_hierarchy:
                available_counties = ["All Counties"] + sorted(geo_hierarchy[selected_region].keys())
            else:
                available_counties = ["All Counties"] + geo_matrix.get("counties", [])

            if st.session_state.get("sel_county") not in available_counties:
                st.session_state["sel_county"] = "All Counties"

            selected_county = st.selectbox("County", options=available_counties, key="sel_county")

        # When County changes, cascade reset to Sub-Recipient
        if selected_county != st.session_state["prev_filter_county"]:
            st.session_state["prev_filter_county"] = selected_county
            st.session_state["sel_sr"] = "All Sub-Recipients"

        with f_col3:
            if selected_region != "All Regions" and selected_county != "All Counties":
                available_srs = ["All Sub-Recipients"] + sorted(geo_hierarchy.get(selected_region, {}).get(selected_county, []))
            elif selected_region != "All Regions":
                all_srs_in_reg = []
                for srs in geo_hierarchy.get(selected_region, {}).values():
                    all_srs_in_reg.extend(srs)
                available_srs = ["All Sub-Recipients"] + sorted(set(all_srs_in_reg))
            else:
                available_srs = ["All Sub-Recipients"] + geo_matrix.get("sub_recipients", [])

            if st.session_state.get("sel_sr") not in available_srs:
                st.session_state["sel_sr"] = "All Sub-Recipients"

            selected_sr = st.selectbox("Sub-Recipient (SR)", options=available_srs, key="sel_sr")

        with f_col4:
            cat_options = [
                "All Indicators",
                "HIV Testing Services (HTS)",
                "PrEP Cascade",
                "Care & Treatment (ART)",
                "Clinical Services (STI/TB)",
                "Commodities & Harm Reduction",
                "Demographics",
            ]
            selected_category = st.selectbox("Indicator Focus", options=cat_options, key="sel_category")

    # Match column name variants case-insensitively
    def _match_column(df: pd.DataFrame | None, *names: str) -> str | None:
        if df is None:
            return None
        col_lut = {c.lower().replace(" ", "_"): c for c in df.columns}
        for n in names:
            k = n.lower().replace(" ", "_")
            if k in col_lut:
                return col_lut[k]
        return None

    # Filter any tabular frame directly without groupby (Strict compliance with D-040 & D-041)
    def _filter_df_by_geo(df: pd.DataFrame | None) -> pd.DataFrame | None:
        if df is None or df.empty:
            return df
        filtered = df
        reg_c = _match_column(filtered, "region", "REGION")
        if reg_c and selected_region != "All Regions":
            filtered = filtered[
                filtered[reg_c].astype(str).str.strip().str.upper() == selected_region.strip().upper()
            ]
        county_c = _match_column(filtered, "county", "COUNTY")
        if county_c and selected_county != "All Counties":
            filtered = filtered[
                filtered[county_c].astype(str).str.strip().str.upper() == selected_county.strip().upper()
            ]
        sr_c = _match_column(filtered, "sr_name", "SR_NAME", "SR Name", "sub_recipient", "sr")
        if sr_c and selected_sr != "All Sub-Recipients":
            filtered = filtered[
                filtered[sr_c].astype(str).str.strip().str.upper() == selected_sr.strip().upper()
            ]
        return filtered

    # Active filter descriptor
    is_filtered = (
        selected_region != "All Regions"
        or selected_county != "All Counties"
        or selected_sr != "All Sub-Recipients"
    )
    filter_tags = []
    if selected_region != "All Regions":
        filter_tags.append(f"Region: {selected_region}")
    if selected_county != "All Counties":
        filter_tags.append(f"County: {selected_county}")
    if selected_sr != "All Sub-Recipients":
        filter_tags.append(f"SR: {selected_sr}")
    filter_label = f" — [{', '.join(filter_tags)}]" if filter_tags else ""

    # Filter all relevant underlying frames directly without groupby
    filtered_summary = _filter_df_by_geo(result.summary_df)
    filtered_reg = _filter_df_by_geo(result.cleaned_register)
    filtered_kp = _filter_df_by_geo(result.cleaned_kplhiv)
    kpi_base_df = disp.get("kpi_summary_df")
    filtered_kpi = _filter_df_by_geo(kpi_base_df)

    # =========================================================================
    # MODULE B: HIV TESTING SERVICES (HTS) CASCADE WATERFALL
    # =========================================================================
    if selected_category in ("All Indicators", "HIV Testing Services (HTS)"):
        st.divider()

        with _section_container("hts_section"):
            st.subheader(f"1. HIV Testing Services (HTS) Cascade — {population} ({period_mode}){filter_label}")
            st.caption("Sequential testing cascade from cohort registered to linkage to ART.")
            st.markdown(_badges_html(population, period_mode, filter_tags), unsafe_allow_html=True)

            if is_filtered:
                hts_data = extract_hts_cascade(filtered_summary, period_mode, filtered_reg)
            else:
                hts_data = disp.get("hts_cascade", {})

            tested = hts_data.get("Tested", 0)
            neg = hts_data.get("Negative", 0)
            pos = hts_data.get("Positive", 0)
            linked = hts_data.get("Linked to ART", hts_data.get("Linked", 0))

            # Display-only labels with adaptive precision for low-positivity populations
            if tested > 0 and pos > 0:
                raw_pos_rate = (pos / tested) * 100.0
                if raw_pos_rate >= 1.0:
                    pos_pct = f"{raw_pos_rate:.1f}%"
                elif raw_pos_rate >= 0.01:
                    pos_pct = f"{raw_pos_rate:.2f}%"
                else:
                    pos_pct = f"{raw_pos_rate:.3f}%"
            else:
                pos_pct = "0.0%"

            link_pct = f"{(linked / pos * 100):.1f}%" if pos > 0 else "0.0%"
            neg_pct = f"{(neg / tested * 100):.1f}%" if tested > 0 else "0.0%"

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Clients Tested", f"{tested:,}", delta="100% Volume")
            col2.metric("Tested Negative", f"{neg:,}", delta=f"{neg_pct} Negative")
            col3.metric(
                "Diagnosed Positive",
                f"{pos:,}",
                delta=f"{pos_pct} Positivity",
                delta_color="inverse" if pos > 0 else "normal",
                help=f"Total clients with confirmed HIV positive test result: {pos:,} ({pos_pct} of tested clients).",
            )
            col4.metric(
                "Linked to ART",
                f"{linked:,}",
                delta=f"{link_pct} Linkage",
                delta_color="normal",
                help=f"Positive clients initiated or linked to ART: {linked:,} ({link_pct} linkage).",
            )

            if tested > 0:
                # Visual rate strip: positivity and linkage as progress bars
                rate1, rate2 = st.columns(2)
                with rate1:
                    st.progress(
                        min(max(pos / tested, 0.0), 1.0),
                        text=f"Positivity Rate — {pos_pct} ({pos:,} of {tested:,} tested positive)",
                    )
                with rate2:
                    st.progress(
                        min(max(linked / pos, 0.0), 1.0) if pos > 0 else 0.0,
                        text=f"Linkage Rate — {link_pct} ({linked:,} of {pos:,} positives linked to ART)",
                    )

                hts_tab1, hts_tab2 = st.tabs(["🌊 Cascade Visualizations", "📊 Complete Indicator Breakdown & Table"])
                with hts_tab1:
                    col_chart_left, col_chart_right = st.columns([1, 1])

                    with col_chart_left:
                        st.markdown("##### 🌊 Testing Outcomes (Volume & Results)")
                        fig_vol = go.Figure(
                            go.Bar(
                                x=["Tested", "Negative", "Positive"],
                                y=[tested, neg, pos],
                                marker=dict(color=["#3B82F6", "#22C55E", "#EF4444"], line=dict(width=0)),
                                text=[f"<b>{tested:,}</b>", f"<b>{neg:,}</b> ({neg_pct})", f"<b>{pos:,}</b> ({pos_pct})"],
                                textposition="outside",
                                cliponaxis=False,
                                hovertemplate="<b>%{x}</b><br>Clients: %{y:,}<extra></extra>",
                            )
                        )
                        fig_vol.update_layout(showlegend=False, bargap=0.35, title=f"Testing Outcomes (n={tested:,})")
                        fig_vol.update_yaxes(title_text="Clients", rangemode="tozero")
                        st.plotly_chart(_polish_figure(fig_vol, height=440), use_container_width=True, config={"displayModeBar": False})

                    with col_chart_right:
                        st.markdown(f"##### 🎯 Positive Identification & ART Linkage ({pos:,} Positives)")
                        max_link = max(pos, linked, 10)
                        fig_link = go.Figure(
                            go.Bar(
                                x=["Diagnosed Positive", "Linked to ART"],
                                y=[pos, linked],
                                marker=dict(color=["#EF4444", "#8B5CF6"], line=dict(width=0)),
                                text=[f"<b>{pos:,}</b> ({pos_pct} Positivity)", f"<b>{linked:,}</b> ({link_pct} Linked)"],
                                textposition="outside",
                                cliponaxis=False,
                                hovertemplate="<b>%{x}</b><br>Clients: %{y:,}<extra></extra>",
                            )
                        )
                        fig_link.update_layout(showlegend=False, bargap=0.35, title=f"Positive Cohort Linkage (n={pos:,})")
                        fig_link.update_yaxes(range=[0, max_link * 1.35], title_text="Positive Clients")
                        st.plotly_chart(_polish_figure(fig_link, height=440), use_container_width=True, config={"displayModeBar": False})

                    with st.expander("ℹ️ How to read these charts"):
                        st.markdown(
                            f"- **Left Panel (Testing Outcomes):** Shows total testing throughput ({tested:,} tested) with {neg:,} negative and **{pos:,} positive ({pos_pct})**.\n"
                            f"- **Right Panel (Positive Linkage Focus):** Zooms in on the **{pos:,} positive clients** to clearly visualize ART initiation. **{linked:,} of {pos:,} ({link_pct})** have documented linkage to treatment.\n"
                            "- This dual-panel view ensures positive clients are prominent and never eclipsed by the large testing denominator."
                        )
                with hts_tab2:
                    full_stages = ["Tested", "Negative", "Positive", "Linked to ART"]
                    full_values = [tested, neg, pos, linked]
                    hts_df = pd.DataFrame(
                        {
                            "Cascade Stage": full_stages,
                            "Clients": full_values,
                            "Percentage": ["100.0%", neg_pct, pos_pct, link_pct],
                        }
                    ).set_index("Cascade Stage")
                    fig_hts_breakdown = _hts_breakdown_figure(
                        full_stages,
                        full_values,
                        title=f"HTS Indicator Breakdown{filter_label}",
                    )
                    st.plotly_chart(fig_hts_breakdown, use_container_width=True, config={"displayModeBar": False})
                    with st.expander("📋 View breakdown as table", expanded=True):
                        st.dataframe(hts_df, use_container_width=True)
            else:
                st.info(f"No HIV testing client records found for selected filter{filter_label}.")

    # =========================================================================
    # MODULE C: PRE-EXPOSURE PROPHYLAXIS (PrEP) CASCADE
    # =========================================================================
    if selected_category in ("All Indicators", "PrEP Cascade"):
        st.divider()

        with _section_container("prep_section"):
            st.subheader(f"2. Pre-Exposure Prophylaxis (PrEP) Cascade — {population}{filter_label}")
            st.caption("Active client status, new initiations, refills, restarts, regimen switches, and discontinuations.")
            st.markdown(_badges_html(population, period_mode, filter_tags), unsafe_allow_html=True)
            prep_data = disp.get("prep_cascade", {})
            if is_filtered or not prep_data or "Restarted" not in prep_data:
                prep_data = extract_prep_cascade(filtered_summary, filtered_reg, period_mode)

            p1, p2, p3, p4, p5, p6 = st.columns(6)
            p_act = prep_data.get("Active on PrEP", prep_data.get("Screened", 0))
            p_init = prep_data.get("Initiated (New)", prep_data.get("Initiated", 0))
            p_ref = prep_data.get("Refills", prep_data.get("Refills / Continuing", 0))
            p_restart = prep_data.get("Restarted", prep_data.get("Restart", 0))
            p_switch = prep_data.get("Switched", 0)
            p_disc = prep_data.get("Discontinued", 0)

            p1.metric("Active on PrEP", f"{p_act:,}")
            p2.metric("Initiated (New)", f"{p_init:,}")
            p3.metric("Refills", f"{p_ref:,}")
            p4.metric("Restarted", f"{p_restart:,}")
            p5.metric("Switched", f"{p_switch:,}")
            p6.metric("Discontinued", f"{p_disc:,}")

            prep_display_dict = {
                "Active on PrEP": p_act,
                "Initiated (New)": p_init,
                "Refills": p_ref,
                "Restarted": p_restart,
                "Switched": p_switch,
                "Discontinued": p_disc,
            }

            if prep_display_dict and any(v > 0 for v in prep_display_dict.values()):
                prep_labels = list(prep_display_dict.keys())
                prep_vals = list(prep_display_dict.values())
                fig_prep = create_grouped_bar(
                    categories=prep_labels,
                    series_dict={"PrEP Clients": prep_vals},
                    title=f"PrEP Programmatic Stage Breakdown{filter_label}",
                    y_label="Key Population Clients",
                )
                fig_prep = _style_bar_figure(fig_prep, _palette("prep_section", len(prep_labels)))
                st.plotly_chart(fig_prep, use_container_width=True, config={"displayModeBar": False})
                with st.expander("ℹ️ How to read this chart"):
                    st.markdown(
                        "- **Active on PrEP** represents unique clients who initiated, refilled, restarted, or switched (sum of Q1 + Q2 for semester, excluding continuing).\n"
                        "- **Initiated (New)** counts clients who started PrEP in the period.\n"
                        "- **Refills** counts clients receiving PrEP drug refills.\n"
                        "- **Restarted** counts clients who restarted PrEP after an interruption or gap in prevention.\n"
                        "- **Switched** counts clients transitioned across PrEP regimens/products.\n"
                        "- **Discontinued** counts clients who stopped PrEP — a rising bar here warrants retention follow-up."
                    )
                _data_table_expander(prep_display_dict)
            else:
                st.info(f"No PrEP programmatic records found for selected filter{filter_label}.")

    # =========================================================================
    # MODULE D: CARE & TREATMENT (95-95-95 CLINICAL CASCADE)
    # =========================================================================
    if selected_category in ("All Indicators", "Care & Treatment (ART)"):
        st.divider()

        with _section_container("art_section"):
            st.subheader(f"3. Antiretroviral Therapy (ART) & Viral Suppression (95-95-95) — {population}{filter_label}")
            st.caption("Clinical cascade for Known Positive clients active on care and viral load suppression.")
            st.markdown(_badges_html(population, period_mode, filter_tags), unsafe_allow_html=True)
            if is_filtered:
                art_data = extract_art_cascade(filtered_summary, filtered_kp, period_mode)
            else:
                art_data = disp.get("art_cascade", {})

            a1, a2, a3, a4 = st.columns(4)
            kpl = art_data.get("Active KPLHIV", 0)
            on_art = art_data.get("On ART", 0)
            vl_done = art_data.get("Viral Load Done", 0)
            supp = art_data.get("Suppressed (<1000 cp/ml)", art_data.get("Suppressed", 0))

            a1.metric("Active KPLHIV", f"{kpl:,}")
            a2.metric("On ART", f"{on_art:,}")
            a3.metric("Viral Load Done", f"{vl_done:,}")
            a4.metric("Suppressed (<1000 cp/ml)", f"{supp:,}")

            if art_data and any(v > 0 for v in [kpl, on_art, vl_done, supp]):
                stages_art = ["Active KPLHIV", "On ART", "Viral Load Done", "Virally Suppressed"]
                values_art = [kpl, on_art, vl_done, supp]
                fig_art_funnel = create_cascade_funnel(
                    stages=stages_art,
                    values=values_art,
                    title=f"95-95-95 Clinical Care & Viral Suppression Cascade{filter_label}",
                )
                fig_art_funnel = _style_funnel_figure(fig_art_funnel, _palette("art_section", len(stages_art)))
                st.plotly_chart(fig_art_funnel, use_container_width=True, config={"displayModeBar": False})
                with st.expander("ℹ️ How to read this chart"):
                    st.markdown(
                        "- Each band is one step of the care cascade, from **Active KPLHIV** down to **Virally Suppressed**.\n"
                        "- The label on each band shows the client count and the **percentage of the previous stage** "
                        "(the conversion from one step to the next).\n"
                        "- The narrowest drop-offs show where clients are being lost from care."
                    )
                _data_table_expander(
                    {
                        "Active KPLHIV": kpl,
                        "On ART": on_art,
                        "Viral Load Done": vl_done,
                        "Virally Suppressed": supp,
                    }
                )
            else:
                st.info(f"No ART or viral suppression records found for selected filter{filter_label}.")

    # =========================================================================
    # MODULE E: CLINICAL SCREENING & MANAGEMENT (STI / TB)
    # =========================================================================
    if selected_category in ("All Indicators", "Clinical Services (STI/TB)"):
        st.divider()

        with _section_container("clin_section"):
            st.subheader(f"4. Clinical Services Management (STI / TB) — {population}{filter_label}")
            st.caption("Routine screening, syndromic management, and treatment completion rates.")
            st.markdown(_badges_html(population, period_mode, filter_tags), unsafe_allow_html=True)
            if is_filtered:
                clin_data = extract_clinical_cascade(filtered_summary, period_mode)
            else:
                clin_data = disp.get("clinical_cascade", {})

            cl1, cl2, cl3, cl4 = st.columns(4)
            sti_s = clin_data.get("STI Screened", 0)
            sti_d = clin_data.get("STI Diagnosed", 0)
            sti_t = clin_data.get("STI Treated", 0)
            tb_s = clin_data.get("TB Screened", 0)

            cl1.metric("STI Screened", f"{sti_s:,}")
            cl2.metric("STI Diagnosed", f"{sti_d:,}")
            cl3.metric("STI Treated", f"{sti_t:,}")
            cl4.metric("TB Screened", f"{tb_s:,}")

            if clin_data and (sti_s > 0 or sti_d > 0 or sti_t > 0 or tb_s > 0):
                # Separate scales to prevent small values (e.g. 15 STI diagnosed) from disappearing
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    fig_sti = create_grouped_bar(
                        categories=["Screened", "Diagnosed", "Treated"],
                        series_dict={"STI Management": [sti_s, sti_d, sti_t]},
                        title=f"Sexually Transmitted Infections (STI) Pathway{filter_label}",
                        y_label="Encounter Consultations",
                    )
                    fig_sti = _style_bar_figure(fig_sti, ["#F59E0B", "#EF4444", "#22C55E"], height=420)
                    st.plotly_chart(fig_sti, use_container_width=True, config={"displayModeBar": False})
                with c_col2:
                    fig_tb = create_grouped_bar(
                        categories=["TB Screened"],
                        series_dict={"TB Screening": [tb_s]},
                        title=f"Tuberculosis (TB) Routine Screening{filter_label}",
                        y_label="Clients Screened",
                    )
                    fig_tb = _style_bar_figure(fig_tb, ["#8B5CF6"], height=420, bargap=0.6)
                    st.plotly_chart(fig_tb, use_container_width=True, config={"displayModeBar": False})
                with st.expander("ℹ️ How to read these charts"):
                    st.markdown(
                        "- **STI pathway** follows clients from *Screened* to *Diagnosed* to *Treated*; "
                        "a gap between Diagnosed and Treated means untreated infections.\n"
                        "- **TB screening** is shown on its own scale so small STI values stay visible "
                        "and are not dwarfed by larger TB screening counts."
                    )
                _data_table_expander(
                    {
                        "STI Screened": sti_s,
                        "STI Diagnosed": sti_d,
                        "STI Treated": sti_t,
                        "TB Screened": tb_s,
                    }
                )
            else:
                st.info(f"No clinical STI/TB screening records found for selected filter{filter_label}.")

    # =========================================================================
    # MODULE F: COMMODITIES & PREVENTION DISTRIBUTION
    # =========================================================================
    if selected_category in ("All Indicators", "Commodities & Harm Reduction"):
        st.divider()

        with _section_container("comm_section"):
            st.subheader(f"5. Commodities Distribution & Harm Reduction — {population}{filter_label}")
            st.caption("Quantities of male condoms, lubricants, peer education contacts, and needle/syringe units (PWID).")
            st.markdown(_badges_html(population, period_mode, filter_tags), unsafe_allow_html=True)
            if is_filtered:
                comm_data = extract_commodities(filtered_summary, filtered_reg, population, period_mode)
            else:
                comm_data = disp.get("commodities", {})

            if comm_data and any(v > 0 for v in comm_data.values()):
                comm_cols = st.columns(len(comm_data))
                for idx, (label, val) in enumerate(comm_data.items()):
                    comm_cols[idx].metric(label, f"{val:,}")

                c_labels = list(comm_data.keys())
                c_vals = list(comm_data.values())
                c_parents = [""] * len(c_labels)
                fig_comm = create_treemap(
                    labels=c_labels,
                    parents=c_parents,
                    values=c_vals,
                    title=f"Commodity Distribution Composition (Units / Contacts){filter_label}",
                )
                fig_comm = _style_treemap_figure(fig_comm, _palette("comm_section", len(c_labels)))
                st.plotly_chart(fig_comm, use_container_width=True, config={"displayModeBar": False})
                with st.expander("ℹ️ How to read this chart"):
                    st.markdown(
                        "- Each tile is one commodity or service; **bigger tiles mean larger quantities** distributed.\n"
                        "- Units (e.g. condoms) and contacts (e.g. peer education) are different measures, "
                        "so compare tile sizes with care."
                    )
                _data_table_expander(comm_data)
            else:
                st.info(f"No commodity distribution records found for selected filter{filter_label}.")

    # =========================================================================
    # MODULE G: DEMOGRAPHIC AGE & SEX DISTRIBUTION (Population Pyramid)
    # =========================================================================
    if selected_category in ("All Indicators", "Demographics"):
        st.divider()

        with _section_container("demo_section"):
            st.subheader(f"6. Demographic Age & Sex Distribution — {population}{filter_label}")
            st.caption("Visual population distribution conforming strictly to typology demographic reporting rules.")
            st.markdown(_badges_html(population, period_mode, filter_tags), unsafe_allow_html=True)

            if is_filtered:
                pyramid_data = extract_demographic_pyramid(filtered_reg, population, summary_df=filtered_summary)
            else:
                pyramid_data = disp.get("demographic_pyramid", {})

            if pyramid_data:
                age_groups = pyramid_data.get("age_groups", ["Below 15", "15–19", "20–24", "25+"])
                males = pyramid_data.get("male_counts", [0, 0, 0, 0])
                females = pyramid_data.get("female_counts", [0, 0, 0, 0])

                fig_pyramid = create_population_pyramid(
                    age_groups=age_groups,
                    male_counts=males,
                    female_counts=females,
                    population=population,
                    title=f"Cohort Age/Sex Distribution — {population}{filter_label}",
                )
                fig_pyramid = _style_pyramid_figure(fig_pyramid)
                st.plotly_chart(fig_pyramid, use_container_width=True, config={"displayModeBar": False})
                with st.expander("ℹ️ How to read this chart"):
                    st.markdown(
                        "- Each row is an **age band**; bars extend left for **males** and right for **females**.\n"
                        "- Age bands follow the reporting rules for this key population typology.\n"
                        "- A lopsided pyramid shows which age and sex groups the programme is reaching, and which it is missing."
                    )
                with st.expander("📋 View data as table"):
                    pyr_tbl = pd.DataFrame(
                        {"Age Group": age_groups, "Male": males, "Female": females}
                    ).set_index("Age Group")
                    st.dataframe(pyr_tbl.style.format(_fmt_num), use_container_width=True)
            else:
                st.info(f"No demographic client records found for selected filter{filter_label}.")

    # =========================================================================
    # MODULE H: DETAILED GEOGRAPHIC & KPI DATA TABLES
    # =========================================================================
    st.divider()

    with _section_container("tables_section"):
        st.subheader(f"7. Standardized Geographic Indicator Summary Table{filter_label}")
        st.caption("Disaggregated facility-level summary table with retained (MISSING) geography.")

        if filtered_summary is not None and not filtered_summary.empty:
            summary_with_total = append_total_row(filtered_summary)
            styled_summary = style_table_with_total_row(summary_with_total)
            st.dataframe(styled_summary, use_container_width=True, hide_index=True)
        else:
            st.info(f"No matching geographic indicator records for selected filter{filter_label}.")

        if filtered_kpi is not None and not filtered_kpi.empty:
            st.markdown("---")
            st.subheader(f"8. KPI Age and Sex Cross-Disaggregation Table{filter_label}")
            st.caption("Key programmatic indicators (Defined Package, HTS, PrEP) categorized by age band and sex (notebook Cell 84).")
            kpi_with_total = append_total_row(filtered_kpi, label_col="sr_name")
            styled_kpi = style_table_with_total_row(kpi_with_total)
            st.dataframe(styled_kpi, use_container_width=True, hide_index=True)
        elif kpi_base_df is not None and not kpi_base_df.empty:
            st.markdown("---")
            st.subheader(f"8. KPI Age and Sex Cross-Disaggregation Table{filter_label}")
            st.info(f"No matching KPI demographic records for selected filter{filter_label}.")

    # =========================================================================
    # MODULE I: WORKFLOW PROGRESSION TO REPORT EXPORTS
    # =========================================================================
    st.divider()
    st.subheader("🏁 Next Workflow Step")
    st.caption("Proceed to Export Reports to generate and download consolidated Global Fund packages.")

    col_inf, col_btn = st.columns([2, 1])
    with col_inf:
        st.info("ℹ️ Navigate to Export Reports to configure reporting period and generate master Excel workbooks.")
    with col_btn:
        if st.button("📥 Proceed to Report Exports ➡️", type="primary", use_container_width=True):
            advance_workflow_stage(WorkflowStage.ANALYTICS_VIEWED)
            st.switch_page("ui/exports.py")


render_analytics()