# chart_plotter.py — Plotly dashboard for India Quant Scoring System

import os
from typing import Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import BUY_THRESHOLD, SELL_THRESHOLD, CHARTS_DIR, CHART_FILENAME

# ── colour palette ──────────────────────────────────────────────────────────
BUY_COLOR  = "#26a69a"
HOLD_COLOR = "#ffa726"
SELL_COLOR = "#ef5350"
NEUTRAL    = "#90a4ae"
BG_COLOR   = "#0d1117"
GRID_COLOR = "#1e2630"
TEXT_COLOR = "#e0e0e0"

SCORE_COLORS = {
    "price_score": "#42a5f5",
    "pe_score":    "#66bb6a",
    "vix_score":   "#ffa726",
    "fx_score":    "#ab47bc",
}

SCORE_LABELS = {
    "price_score": "Price",
    "pe_score":    "P/E",
    "vix_score":   "VIX",
    "fx_score":    "FX",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _signal_color(score: float) -> str:
    if score < BUY_THRESHOLD:
        return BUY_COLOR
    if score > SELL_THRESHOLD:
        return SELL_COLOR
    return HOLD_COLOR


def _signal_label(score: float) -> str:
    if score < BUY_THRESHOLD:
        return "🟢 BUY"
    if score > SELL_THRESHOLD:
        return "🔴 SELL"
    return "🟡 HOLD"


# ── Section 1: Gauge charts ──────────────────────────────────────────────────

def _gauge_figure(scores: dict) -> go.Figure:
    assets = list(scores.keys())
    n    = len(assets)
    cols = min(n, 4)
    rows = (n + cols - 1) // cols

    specs = [[{"type": "indicator"}] * cols for _ in range(rows)]
    fig = make_subplots(
        rows=rows, cols=cols,
        specs=specs,
        subplot_titles=[
            f"{a}  {_signal_label(scores[a].get('master_score', 0))}"
            for a in assets
        ],
    )

    for idx, asset in enumerate(assets):
        row   = idx // cols + 1
        col   = idx %  cols + 1
        total = float(scores[asset].get("master_score") or 0)

        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=round(total, 3),
                number={"font": {"color": _signal_color(total), "size": 28}},
                gauge={
                    "axis": {"range": [0, 1], "tickcolor": TEXT_COLOR,
                              "tickfont": {"color": TEXT_COLOR}},
                    "bar":     {"color": _signal_color(total), "thickness": 0.25},
                    "bgcolor": GRID_COLOR,
                    "steps": [
                        {"range": [0,             BUY_THRESHOLD],  "color": "#1b3a35"},
                        {"range": [BUY_THRESHOLD, SELL_THRESHOLD], "color": "#2e2a1a"},
                        {"range": [SELL_THRESHOLD, 1],             "color": "#3a1a1a"},
                    ],
                    "threshold": {"line": {"color": TEXT_COLOR, "width": 2},
                                  "thickness": 0.75, "value": total},
                },
            ),
            row=row, col=col,
        )

    fig.update_layout(
        title_text="<b>Master Score — Entry / Exit Signal</b>",
        title_font={"color": TEXT_COLOR, "size": 18},
        paper_bgcolor=BG_COLOR, font_color=TEXT_COLOR,
        height=300 * rows,
        margin={"t": 80, "b": 20, "l": 20, "r": 20},
    )
    for ann in fig.layout.annotations:
        ann.font.color = TEXT_COLOR
    return fig


# ── Section 2: Sub-score bar chart ───────────────────────────────────────────

def _subscore_figure(scores: dict) -> go.Figure:
    assets     = list(scores.keys())
    components = ["price_score", "pe_score", "vix_score", "fx_score"]

    fig = go.Figure()
    for comp in components:
        values = [round(float(scores[a].get(comp) or 0), 3) for a in assets]
        fig.add_trace(go.Bar(
            name=SCORE_LABELS[comp],
            x=assets, y=values,
            marker_color=SCORE_COLORS[comp],
            text=[f"{v:.2f}" for v in values],
            textposition="outside",
            textfont={"color": TEXT_COLOR},
        ))

    fig.add_hline(y=BUY_THRESHOLD,  line_dash="dash", line_color=BUY_COLOR,
                  annotation_text="BUY threshold",  annotation_font_color=BUY_COLOR)
    fig.add_hline(y=SELL_THRESHOLD, line_dash="dash", line_color=SELL_COLOR,
                  annotation_text="SELL threshold", annotation_font_color=SELL_COLOR)

    fig.update_layout(
        title_text="<b>Sub-Score Breakdown by Asset</b>",
        title_font={"color": TEXT_COLOR, "size": 16},
        barmode="group",
        paper_bgcolor=BG_COLOR, plot_bgcolor=GRID_COLOR, font_color=TEXT_COLOR,
        yaxis={"range": [0, 1.2], "gridcolor": BG_COLOR, "title": "Score (0–1)"},
        xaxis={"title": "Asset"},
        legend={"bgcolor": BG_COLOR, "bordercolor": NEUTRAL},
        height=420, margin={"t": 60, "b": 40},
    )
    return fig


# ── Section 3: 52-Week Range chart (% normalised) ────────────────────────────

def _range_figure(asset_data: dict) -> go.Figure:
    """
    FIX: All assets normalised to 0-100% position in their own 52W band.
    This solves the Nifty (23000) vs stocks (1000-3000) scale mismatch
    where Nifty's bar used to stretch far off to the right.
    
    X-axis now shows 0% (52W Low) → 100% (52W High) for every asset.
    Actual ₹ prices are shown as labels and in hover tooltip.
    """
    assets = [a for a in asset_data if a != "macro"]
    fig    = go.Figure()

    for asset in assets:
        d = asset_data[asset]

        # Handle both flat and nested price formats
        if isinstance(d.get("price"), dict):
            curr = float(d["price"].get("current") or 0)
            low  = float(d["price"].get("low_52w")  or 0)
            high = float(d["price"].get("high_52w") or 0)
        else:
            curr = float(d.get("price")    or 0)
            low  = float(d.get("low_52w")  or 0)
            high = float(d.get("high_52w") or 0)

        if high <= low or curr == 0:
            continue

        # Normalise to percentage position in 52W range
        pct       = max(0.0, min(1.0, (curr - low) / (high - low)))
        pct_disp  = round(pct * 100, 1)   # 0–100 for display
        color     = _signal_color(pct)

        # Full range bar: always 0 to 100
        fig.add_trace(go.Bar(
            x=[100],
            base=[0],
            y=[asset],
            orientation="h",
            marker_color=GRID_COLOR,
            marker_line_width=0,
            showlegend=False,
            hoverinfo="skip",
        ))

        # BUY zone (0 → BUY_THRESHOLD*100)
        fig.add_trace(go.Bar(
            x=[BUY_THRESHOLD * 100],
            base=[0],
            y=[asset],
            orientation="h",
            marker_color="#1b3a35",
            marker_line_width=0,
            showlegend=False,
            hoverinfo="skip",
        ))

        # SELL zone (SELL_THRESHOLD*100 → 100)
        fig.add_trace(go.Bar(
            x=[100 - SELL_THRESHOLD * 100],
            base=[SELL_THRESHOLD * 100],
            y=[asset],
            orientation="h",
            marker_color="#3a1a1a",
            marker_line_width=0,
            showlegend=False,
            hoverinfo="skip",
        ))

        # Current price diamond marker at pct position
        fig.add_trace(go.Scatter(
            x=[pct_disp],
            y=[asset],
            mode="markers+text",
            marker={"size": 14, "color": color, "symbol": "diamond",
                    "line": {"color": TEXT_COLOR, "width": 1}},
            text=[f"  ₹{curr:,.1f}"],
            textposition="middle right",
            textfont={"color": color, "size": 11},
            showlegend=False,
            hovertemplate=(
                f"<b>{asset}</b><br>"
                f"Current : ₹{curr:,.2f}<br>"
                f"52W Low : ₹{low:,.2f}<br>"
                f"52W High: ₹{high:,.2f}<br>"
                f"Position: {pct_disp:.1f}%"
                f"<extra></extra>"
            ),
        ))

        # Low label at x=0
        fig.add_annotation(
            x=0, y=asset,
            text=f"₹{low:,.0f}",
            showarrow=False,
            xanchor="right",
            xshift=-6,
            font={"color": BUY_COLOR, "size": 10},
        )

        # High label at x=100
        fig.add_annotation(
            x=100, y=asset,
            text=f"₹{high:,.0f}",
            showarrow=False,
            xanchor="left",
            xshift=6,
            font={"color": SELL_COLOR, "size": 10},
        )

    # Threshold vertical lines
    fig.add_vline(x=BUY_THRESHOLD * 100,  line_dash="dash",
                  line_color=BUY_COLOR,  line_width=1,
                  annotation_text="BUY",
                  annotation_font_color=BUY_COLOR,
                  annotation_position="top")
    fig.add_vline(x=SELL_THRESHOLD * 100, line_dash="dash",
                  line_color=SELL_COLOR, line_width=1,
                  annotation_text="SELL",
                  annotation_font_color=SELL_COLOR,
                  annotation_position="top")

    fig.update_layout(
        title_text="<b>52-Week Price Range — Current Position (% of range)</b>",
        title_font={"color": TEXT_COLOR, "size": 16},
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        font_color=TEXT_COLOR,
        xaxis={
            "title": "Position in 52-Week Range (%)",
            "range": [-5, 140],          # extra right margin for ₹ labels
            "gridcolor": GRID_COLOR,
            "ticksuffix": "%",
            "tickvals": [0, 25, 35, 50, 65, 75, 100],
        },
        yaxis={"autorange": "reversed"},
        height=340,
        barmode="overlay",
        margin={"t": 70, "b": 50, "l": 90, "r": 20},
    )
    return fig


# ── Section 4: Macro panel ────────────────────────────────────────────────────

def _macro_figure(macro_data: dict) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=["India VIX", "USD / INR"],
    )

    panels = [
        ("vix",    10.0, 35.0, True,  1),
        ("usdinr", 70.0, 90.0, True,  2),
    ]

    for key, default_min, default_max, invert, col_idx in panels:
        raw = macro_data.get(key)
        if isinstance(raw, dict):
            curr = float(raw.get("current") or raw.get(key) or 0)
            vmin = float(raw.get("min", default_min))
            vmax = float(raw.get("max", default_max))
        else:
            curr = float(raw or 0)
            vmin = default_min
            vmax = default_max

        norm  = max(0.0, min(1.0, (curr - vmin) / (vmax - vmin) if vmax != vmin else 0.5))
        color = _signal_color(1 - norm if invert else norm)

        fig.add_trace(
            go.Indicator(
                mode="number+gauge+delta",
                value=round(curr, 2),
                delta={
                    "reference":   round((vmin + vmax) / 2, 2),
                    "valueformat": ".2f",
                    "increasing":  {"color": SELL_COLOR},
                    "decreasing":  {"color": BUY_COLOR},
                },
                number={"font": {"color": color, "size": 30}},
                gauge={
                    "axis": {"range": [vmin, vmax], "tickcolor": TEXT_COLOR,
                              "tickfont": {"color": TEXT_COLOR}},
                    "bar":     {"color": color, "thickness": 0.25},
                    "bgcolor": GRID_COLOR,
                    "steps": [
                        {"range": [vmin, vmin + (vmax - vmin) * BUY_THRESHOLD],                           "color": "#1b3a35"},
                        {"range": [vmin + (vmax - vmin) * BUY_THRESHOLD, vmin + (vmax - vmin) * SELL_THRESHOLD], "color": "#2e2a1a"},
                        {"range": [vmin + (vmax - vmin) * SELL_THRESHOLD, vmax],                          "color": "#3a1a1a"},
                    ],
                },
            ),
            row=1, col=col_idx,
        )

    fig.update_layout(
        title_text="<b>Macro Panel — VIX & USD/INR</b>",
        title_font={"color": TEXT_COLOR, "size": 16},
        paper_bgcolor=BG_COLOR, font_color=TEXT_COLOR,
        height=280, margin={"t": 70, "b": 20},
    )
    for ann in fig.layout.annotations:
        ann.font.color = TEXT_COLOR
    return fig


# ── Master builder ────────────────────────────────────────────────────────────

def build_dashboard(
    scores:     dict,
    asset_data: dict,
    macro_data: dict,
    filepath:   Optional[str] = None,
) -> str:
    if filepath is None:
        os.makedirs(CHARTS_DIR, exist_ok=True)
        filepath = os.path.join(CHARTS_DIR, CHART_FILENAME)
    else:
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)

    print("  Building gauge chart…")
    fig_gauge = _gauge_figure(scores)
    print("  Building sub-score bars…")
    fig_bars  = _subscore_figure(scores)
    print("  Building 52W range chart…")
    fig_range = _range_figure(asset_data)
    print("  Building macro panel…")
    fig_macro = _macro_figure(macro_data)

    html_parts = [
        "<html><head><meta charset='utf-8'>",
        "<title>India Quant Dashboard</title>",
        "<meta http-equiv='refresh' content='60'>",
        "<style>body{background:#0d1117;margin:0;padding:16px;font-family:sans-serif;}</style>",
        "</head><body>",
        "<h2 style='color:#e0e0e0;text-align:center;'>India Quant Scoring Dashboard</h2>",
        fig_gauge.to_html(full_html=False, include_plotlyjs="cdn"),
        fig_bars.to_html (full_html=False, include_plotlyjs=False),
        fig_range.to_html(full_html=False, include_plotlyjs=False),
        fig_macro.to_html(full_html=False, include_plotlyjs=False),
        "</body></html>",
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"  ✅ Dashboard saved → {os.path.abspath(filepath)}")
    return os.path.abspath(filepath)


# ── smoke-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _scores = {
        "Nifty":    {"master_score": 0.28, "price_score": 0.25, "pe_score": 0.30, "vix_score": 0.22, "fx_score": 0.35},
        "Infosys":  {"master_score": 0.55, "price_score": 0.60, "pe_score": 0.55, "vix_score": 0.45, "fx_score": 0.58},
        "Reliance": {"master_score": 0.70, "price_score": 0.72, "pe_score": 0.68, "vix_score": 0.65, "fx_score": 0.75},
        "ICICI":    {"master_score": 0.42, "price_score": 0.40, "pe_score": 0.45, "vix_score": 0.38, "fx_score": 0.44},
    }
    _asset_data = {
        "Nifty":    {"price": 23689, "high_52w": 26373, "low_52w": 22183},
        "Infosys":  {"price": 1592,  "high_52w": 2006,  "low_52w": 1358},
        "Reliance": {"price": 1313,  "high_52w": 1608,  "low_52w": 1156},
        "ICICI":    {"price": 1298,  "high_52w": 1438,  "low_52w": 1005},
    }
    _macro_data = {"vix": 18.61, "usdinr": 84.2}
    path = build_dashboard(_scores, _asset_data, _macro_data, filepath="output/quant_dashboard_test.html")
    print(f"Saved: {path}")