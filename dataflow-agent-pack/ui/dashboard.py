"""DATAFLOW Dashboard Page — Executive Performance Cockpit.

Primary Audience: Programme Managers, Directors, Regional Coordinators, Operational Leads.
Primary Question: "What is happening in the programme, how are we performing, and where should management pay attention?"

Strictly adheres to Master Brief §11 and Decisions D-040/D-041:
- Zero analytical calculations, groupby, or formulas in ui/ (pure presentation).
- All metric cards trace directly to session pipeline result and runtime metadata.
- Clear persona distinction: Executive summary and alerts without overloading raw tables.
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

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from analytics.visualizations.charts import (  # noqa: E402
    create_lollipop_chart,
    create_regional_heatmap,
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
# Same visual language as the Analytics page: every block lives in a keyed
# container (st-key-<name>) so the CSS only touches that block.
_ACCENT_BLUE = "#3B82F6"
_ACCENT_VIOLET = "#8B5CF6"
_ACCENT_TEAL = "#14B8A6"
_ACCENT_GREEN = "#22C55E"
_ACCENT_AMBER = "#F59E0B"
_ACCENT_RED = "#EF4444"

_SECTION_ACCENTS: dict[str, list[str]] = {
    # 3rd card (DQA) accent is overridden at runtime from the severity counts
    "kpi_section": [_ACCENT_BLUE, _ACCENT_VIOLET, _ACCENT_AMBER, _ACCENT_TEAL],
    "exec_section": ["#6366F1", _ACCENT_BLUE, "#06B6D4", _ACCENT_GREEN],
}

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
"""

_SHARED_CSS = """
/* ---- hero banner ---- */
.dfx-hero {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 16px;
    padding: 20px 26px; margin: 4px 0 18px 0;
    border-radius: 18px;
    border: 1px solid rgba(128, 128, 128, 0.25);
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(139, 92, 246, 0.14));
}
.dfx-hero .title { font-size: 1.2rem; font-weight: 700; margin: 0 0 4px 0; }
.dfx-hero .sub { font-size: 0.88rem; opacity: 0.78; }
.dfx-hero .pills { display: flex; flex-wrap: wrap; gap: 8px; }

/* ---- pills / badges ---- */
.dfx-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 999px;
    font-size: 0.82rem; font-weight: 700;
    border: 1px solid rgba(128, 128, 128, 0.35);
    background: rgba(128, 128, 128, 0.10);
}
.dfx-pill.ok   { background: rgba(34, 197, 94, 0.15);  border-color: rgba(34, 197, 94, 0.55); }
.dfx-pill.warn { background: rgba(245, 158, 11, 0.16); border-color: rgba(245, 158, 11, 0.55); }
.dfx-pill.bad  { background: rgba(239, 68, 68, 0.15);  border-color: rgba(239, 68, 68, 0.55); }
.dfx-pill.info { background: rgba(59, 130, 246, 0.14); border-color: rgba(59, 130, 246, 0.45); }
.dfx-pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 14px 0; }

/* ---- SR podium ---- */
.dfx-podium { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 10px 0; }
.dfx-podium .item {
    padding: 6px 12px; border-radius: 12px;
    font-size: 0.84rem; font-weight: 600;
    background: rgba(128, 128, 128, 0.08);
    border: 1px solid rgba(128, 128, 128, 0.25);
}

/* ---- frames for charts, expanders and the next-step card ---- */
.st-key-perf_section [data-testid="stPlotlyChart"],
.st-key-health_section [data-testid="stPlotlyChart"] {
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 14px;
    padding: 6px;
}
.st-key-health_section [data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid rgba(128, 128, 128, 0.22);
}
.st-key-next_section {
    border: 1px solid rgba(59, 130, 246, 0.35);
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(139, 92, 246, 0.06));
    border-radius: 16px;
    padding: 14px 18px 8px 18px;
}
"""


def _build_css(dqa_accent: str) -> str:
    """Assemble the scoped stylesheet (the DQA card accent follows severity)."""
    parts = ["<style>"]
    for key, accents in _SECTION_ACCENTS.items():
        parts.append(_CARD_CSS_TEMPLATE.replace("__K__", key))
        for i, color in enumerate(accents, start=1):
            if key == "kpi_section" and i == 3:
                color = dqa_accent
            parts.append(
                f'.st-key-{key} [data-testid="stHorizontalBlock"] > div:nth-child({i}) '
                f'[data-testid="stMetric"] {{ border-left-color: {color}; }}'
            )
    parts.append(_SHARED_CSS)
    parts.append("</style>")
    return "\n".join(parts)


def _section_container(key: str):
    """Keyed container so the CSS above only touches this block.

    Streamlit < 1.39 does not support container keys; in that case we fall back
    to a plain container (everything still renders, the styling just does not
    apply).
    """
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


def _dqa_status(crit: int, major: int) -> tuple[str, str, str]:
    """(css class, label, accent colour) for the DQA severity pill and card."""
    if crit > 0:
        return "bad", "Critical issues found", _ACCENT_RED
    if major > 0:
        return "warn", "Review recommended", _ACCENT_AMBER
    return "ok", "Verified clean", _ACCENT_GREEN


def _esc(value) -> str:
    return html.escape(str(value))


def _fmt_rate(value) -> str:
    """Display a precomputed rate as 'NN.N%' (falls back to the raw value)."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return f"{value}%"


def _meter_value(rate) -> float | None:
    """Precomputed % rate -> 0..1 for st.progress (None if not numeric)."""
    try:
        return min(max(float(rate) / 100.0, 0.0), 1.0)
    except (TypeError, ValueError):
        return None


def _hero_html(population, period_mode, file_name, ts, duration, crit, major, minor) -> str:
    status_cls, status_label, _ = _dqa_status(crit, major)
    return (
        '<div class="dfx-hero">'
        "<div>"
        '<div class="title">Latest pipeline run</div>'
        f'<div class="sub">👥 {_esc(population)} &nbsp;·&nbsp; 🗓️ {_esc(period_mode)} '
        f"&nbsp;·&nbsp; 📄 {_esc(file_name)}</div>"
        f'<div class="sub">🕒 {_esc(ts)}</div>'
        "</div>"
        '<div class="pills">'
        f'<span class="dfx-pill {status_cls}">🛡️ {status_label}</span>'
        f'<span class="dfx-pill info">⏱️ {duration:.2f}s</span>'
        "</div>"
        "</div>"
    )


def _dqa_pills_html(crit: int, major: int, minor: int) -> str:
    return (
        '<div class="dfx-pills">'
        f'<span class="dfx-pill bad">🔴 {crit:,} Critical</span>'
        f'<span class="dfx-pill warn">🟠 {major:,} Major</span>'
        f'<span class="dfx-pill info">🔵 {minor:,} Minor</span>'
        "</div>"
    )


def _podium_html(sr_perf: list) -> str:
    """Top-3 Sub-Recipients exactly as ranked by the pipeline (no re-sorting)."""
    medals = ["🥇", "🥈", "🥉"]
    items = []
    for medal, s in zip(medals, sr_perf[:3]):
        items.append(
            f'<span class="item">{medal} {_esc(s.get("sr_name", ""))} — '
            f'{_fmt_rate(s.get("testing_rate", 0.0))}</span>'
        )
    return f'<div class="dfx-podium">{"".join(items)}</div>' if items else ""


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


def _style_heatmap_figure(fig: go.Figure, height: int) -> go.Figure:
    """Tiled heatmap with an in-cell % label and a calm blue scale."""
    fig.update_traces(
        selector=dict(type="heatmap"),
        colorscale=[[0.0, "#EFF6FF"], [0.5, "#60A5FA"], [1.0, "#1E3A8A"]],
        xgap=4,
        ygap=4,
        texttemplate="%{z:.1f}%",
        textfont=dict(size=14),
        colorbar=dict(title="%", thickness=14, len=0.9),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
    )
    fig = _polish_figure(fig, height=height)
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


def _style_lollipop_figure(fig: go.Figure, height: int) -> go.Figure:
    """Bigger, outlined markers and softer stems (keeps any colour the chart already encodes)."""
    for trace in fig.data:
        if getattr(trace, "type", "") != "scatter":
            continue
        mode = str(getattr(trace, "mode", "") or "")
        if "markers" in mode:
            trace.marker.size = 15
            if trace.marker.color is None:
                trace.marker.color = _ACCENT_BLUE
            trace.marker.line = dict(width=2, color="white")
        elif "lines" in mode:
            trace.line.width = 3
            if trace.line.color is None:
                trace.line.color = "rgba(128,128,128,0.45)"
    fig.update_xaxes(ticksuffix="%", rangemode="tozero")
    return _polish_figure(fig, height=height)


def _timings_figure(timings: dict) -> go.Figure:
    """Compact horizontal bar chart of the pipeline stage timings."""
    stages = [str(k).title() for k in timings.keys()]
    secs = list(timings.values())
    fig = go.Figure(
        go.Bar(
            y=stages,
            x=secs,
            orientation="h",
            marker=dict(color=_ACCENT_TEAL, line=dict(width=0)),
            text=[f"{v:.3f}s" for v in secs],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:.3f}s<extra></extra>",
        )
    )
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_yaxes(autorange="reversed")
    fig = _polish_figure(fig, height=max(220, 46 * len(stages) + 70))
    fig.update_layout(margin=dict(l=10, r=50, t=10, b=10))
    return fig


def render_dashboard() -> None:
    st.title("📊 Cohort Performance Dashboard")
    st.caption("Executive Performance Cockpit — High-level programme indicators and regional performance.")

    # Guard check
    if not render_access_guard("Dashboard"):
        return

    # Record dashboard viewed in session and advance workflow to unlock Analytics
    st.session_state["dashboard_viewed"] = True
    if get_current_workflow_stage() == WorkflowStage.DQA_REVIEWED:
        advance_workflow_stage(WorkflowStage.DASHBOARD_VIEWED)

    # 1. Retrieve active session pipeline result (resolving current upload if present)
    res = get_active_pipeline_result()
    if not res:
        st.warning("No active processed pipeline result found in this session.")
        return

    total_cohort = res.total_cohort
    active_kplhiv = res.active_kplhiv
    total_dqa = res.total_dqa_exceptions
    duration = res.duration_seconds
    crit_count = res.critical_dqa_count
    major_count = res.major_dqa_count
    minor_count = res.minor_dqa_count
    population = res.population
    period_mode = res.period_mode
    file_name = res.input_file_name
    file_hash = res.input_file_hash
    ts = res.timestamp
    timings = res.stage_timings
    disp = res.display_analytics or {}

    # One stylesheet for the whole page (scoped per block via container keys)
    _, _, dqa_accent = _dqa_status(crit_count, major_count)
    st.markdown(_build_css(dqa_accent), unsafe_allow_html=True)

    # Run-context hero banner (population, period, file, DQA status, duration)
    st.markdown(
        _hero_html(population, period_mode, file_name, ts, duration, crit_count, major_count, minor_count),
        unsafe_allow_html=True,
    )

    # =========================================================================
    # SECTION A: PROGRAMME OVERVIEW (Topline KPI Metrics)
    # =========================================================================
    with _section_container("kpi_section"):
        st.subheader("1. Programme Health Overview")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            label="Total Cohort Clients",
            value=f"{total_cohort:,}",
            help="Total deduplicated client records in the registered cohort.",
        )
        col2.metric(
            label="Active KPLHIV",
            value=f"{active_kplhiv:,}",
            help="Clients active on ART in the KPLHIV tracking sheet.",
        )
        col3.metric(
            label="DQA Exceptions",
            value=f"{total_dqa:,}",
            delta=f"{crit_count} Critical" if crit_count > 0 else "0 Critical",
            delta_color="inverse" if crit_count > 0 else "normal",
            help="Quality assurance exceptions found across all rules.",
        )
        col4.metric(
            label="Pipeline Duration",
            value=f"{duration:.2f}s",
            help="Total wall-clock duration of the last pipeline run.",
        )

    # Executive Coverage Performance Cards
    exec_kpis = disp.get("executive_metrics", {})
    if exec_kpis:
        st.markdown("---")

        with _section_container("exec_section"):
            k1, k2, k3, k4 = st.columns(4)

            dp_count = exec_kpis.get("defined_package", 0)
            dp_rate = exec_kpis.get("defined_package_rate", 0.0)
            tested_count = exec_kpis.get("hts_tested", 0)
            tested_rate = exec_kpis.get("testing_rate", 0.0)
            pos_count = exec_kpis.get("hts_positive", 0)
            pos_rate = exec_kpis.get("hts_positivity_rate", 0.0)
            if pos_count > 0 and pos_rate < 0.1:
                pos_rate_str = f"{(pos_count / tested_count * 100):.2f}%" if tested_count > 0 else f"{pos_rate:.2f}%"
            else:
                pos_rate_str = f"{pos_rate:.1f}%"
            prep_count = exec_kpis.get("prep_active", 0)
            supp_count = exec_kpis.get("virally_suppressed", 0)
            supp_rate = exec_kpis.get("suppression_rate", 0.0)

            k1.metric(
                label="Defined Package Reached",
                value=f"{dp_count:,}",
                delta=f"{dp_rate}% Cohort",
                help="Clients receiving standard Global Fund defined prevention package.",
            )
            k2.metric(
                label="HTS Clients Tested",
                value=f"{tested_count:,}",
                delta=f"{pos_count:,} Positive ({pos_rate_str})" if pos_count > 0 else f"{tested_rate}% Reached",
                help=f"Total registered clients tested for HIV: {tested_count:,} ({tested_rate}% reached). Diagnosed positive: {pos_count:,} ({pos_rate_str} positivity).",
            )
            k3.metric(
                label="Active on PrEP",
                value=f"{prep_count:,}",
                help="Total key population clients actively on PrEP (Initiated, Refill, Restart, or Switched).",
            )
            k4.metric(
                label="Virally Suppressed",
                value=f"{supp_count:,}",
                delta=f"{supp_rate}% VL Done",
                delta_color="normal",
                help="KPLHIV clients with documented viral load suppression (<1,000 cp/ml).",
            )

            # Coverage meters: the pipeline's precomputed rates drawn as progress bars
            meters = [
                ("Defined package coverage", dp_rate),
                ("HTS testing coverage", tested_rate),
                ("Viral load suppression", supp_rate),
            ]
            meter_cols = st.columns(3)
            for col, (label, rate) in zip(meter_cols, meters):
                frac = _meter_value(rate)
                if frac is not None:
                    col.progress(frac, text=f"{label} — {_fmt_rate(rate)}")

    # =========================================================================
    # SECTION B: REGIONAL PERFORMANCE & SR RANKINGS
    # =========================================================================
    reg_perf = disp.get("regional_performance", [])
    sr_perf = disp.get("sr_rankings", [])

    if reg_perf or sr_perf:
        st.divider()

        with _section_container("perf_section"):
            st.subheader("2. Regional & Sub-Recipient Performance")
            st.caption("Geographic comparison of testing coverage, prevention package, and PrEP uptake.")

            # Shared chart height so the two charts sit level with each other
            perf_rows = max(len(reg_perf), min(len(sr_perf), 10))
            perf_height = max(380, 44 * perf_rows + 150)

            reg_col, sr_col = st.columns([1, 1])

            with reg_col:
                st.markdown("##### 🗺️ Regional Coverage Heatmap")
                if reg_perf:
                    x_ind = ["HTS Testing Rate", "Defined Package Rate", "PrEP Rate"]
                    y_reg = [r["region"] for r in reg_perf]
                    z_vals = [
                        [r.get("testing_rate", 0.0), r.get("dp_rate", 0.0), r.get("prep_rate", 0.0)]
                        for r in reg_perf
                    ]
                    fig_hm = create_regional_heatmap(
                        x_labels=x_ind,
                        y_labels=y_reg,
                        z_data=z_vals,
                        title="Regional Coverage Matrix (%)",
                    )
                    fig_hm = _style_heatmap_figure(fig_hm, height=perf_height)
                    st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
                    with st.expander("ℹ️ How to read this chart"):
                        st.markdown(
                            "- Each row is a **region** and each column is a coverage indicator.\n"
                            "- **Darker tiles mean higher coverage**; the percentage is printed in each tile.\n"
                            "- Look for pale tiles: those regions are lagging on that indicator."
                        )
                else:
                    st.info("No regional aggregation available.")

            with sr_col:
                st.markdown("##### 🏆 Sub-Recipient Testing Coverage Ranking")
                if sr_perf:
                    sr_names = [s["sr_name"] for s in sr_perf[:10]]  # Top 10 SRs
                    sr_rates = [s.get("testing_rate", 0.0) for s in sr_perf[:10]]
                    st.markdown(_podium_html(sr_perf), unsafe_allow_html=True)
                    fig_lol = create_lollipop_chart(
                        categories=sr_names,
                        values=sr_rates,
                        title="SR HTS Testing Coverage (%)",
                        x_label="Testing Coverage (%)",
                    )
                    fig_lol = _style_lollipop_figure(fig_lol, height=perf_height)
                    st.plotly_chart(fig_lol, use_container_width=True, config={"displayModeBar": False})
                    with st.expander("ℹ️ How to read this chart"):
                        st.markdown(
                            "- Each dot is a **Sub-Recipient**; the further right, the higher its HTS testing coverage.\n"
                            "- The medals above the chart show the three best-ranked Sub-Recipients.\n"
                            "- Sub-Recipients at the left end are the first candidates for support."
                        )
                else:
                    st.info("No Sub-Recipient ranking available.")

    # =========================================================================
    # SECTION C: WORKFLOW PROGRESSION TO ANALYTICS
    # =========================================================================
    st.divider()

    with _section_container("next_section"):
        st.subheader("🏁 Next Workflow Step")
        st.caption("Proceed to deep-dive analytics, interactive cascading filters, and demographic disaggregations.")

        col_inf, col_btn = st.columns([2, 1])
        with col_inf:
            st.info("ℹ️ Navigate to Analytics to inspect facility-level indicator tables and cascade funnels.")
        with col_btn:
            if st.button("📈 Proceed to Analytics ➡️", type="primary", use_container_width=True):
                advance_workflow_stage(WorkflowStage.DASHBOARD_VIEWED)
                st.switch_page("ui/analytics.py")


render_dashboard()