"""
app.py — Live Quant Dashboard (Dash)
=====================================
Run:  python app.py
Open: http://127.0.0.1:8050
"""

import logging
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

import config as cfg
from data_fetcher import fetch_all
from scorer import score_all

log = logging.getLogger(__name__)

# ── RSI Calculator ─────────────────────────────────────────────────────────
def compute_rsi(ticker_symbol: str, period: int = 14):
    try:
        import yfinance as yf
        df = yf.download(ticker_symbol, period="3mo", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < period + 1:
            return None
        if isinstance(df.columns, __import__('pandas').MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close  = df["Close"].squeeze()
        delta  = close.diff()
        gain   = delta.clip(lower=0).rolling(period).mean()
        loss   = (-delta.clip(upper=0)).rolling(period).mean()
        rs     = gain / loss
        rsi    = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except Exception as e:
        log.warning("RSI fetch failed for %s: %s", ticker_symbol, e)
        return None

# ── Colour system ───────────────────────────────────────────────────────────
BG       = "#070d14"
SURFACE  = "#0e1621"
CARD     = "#131f2e"
BORDER   = "#1e2d3d"
ACCENT   = "#00d4ff"
ACCENT2  = "#7c3aed"
BUY_C    = "#00e5a0"
HOLD_C   = "#f59e0b"
SELL_C   = "#f43f5e"
SBUY_C   = "#00ff88"   # strong buy
TEXT     = "#e2eaf5"
MUTED    = "#5a7a9a"
GRID     = "#111c28"

def _sc(score):
    if score is None: return MUTED
    if score < cfg.BUY_THRESHOLD:  return BUY_C
    if score > cfg.SELL_THRESHOLD: return SELL_C
    return HOLD_C

def _sl(score):
    if score is None: return "N/A"
    if score < cfg.BUY_THRESHOLD:  return "BUY"
    if score > cfg.SELL_THRESHOLD: return "SELL"
    return "HOLD"

def _sig_icon(sig):
    return {"BUY": "▲", "SELL": "▼", "HOLD": "●", "STRONG BUY": "★"}.get(sig, "●")

# ── Data fetch ──────────────────────────────────────────────────────────────
def get_data():
    try:
        all_data   = fetch_all()
        macro      = all_data.pop("macro", {})
        asset_data = dict(all_data)
        combined   = dict(asset_data)
        combined["macro"] = macro

        scores = score_all(combined)

        # Inject RSI + Strong Buy into scores
        for name, ticker in cfg.ASSETS.items():
            rsi = compute_rsi(ticker)
            if name in scores:
                scores[name]["rsi"] = rsi
                master = scores[name].get("master_score") or 1
                scores[name]["strong_buy"] = (
                    rsi is not None and rsi < 30 and master < 0.35
                )

        return scores, asset_data, macro
    except Exception as e:
        log.error("Pipeline error: %s", e)
        return {}, {}, {}

# ── Chart builders ──────────────────────────────────────────────────────────
SCORE_COLORS = {
    "price_score": "#00d4ff",
    "pe_score":    "#00e5a0",
    "vix_score":   "#f59e0b",
    "fx_score":    "#c084fc",
}

def gauges_fig(scores):
    assets = list(scores.keys())
    fig = make_subplots(
        rows=1, cols=len(assets),
        specs=[[{"type": "indicator"}] * len(assets)],
    )
    for i, asset in enumerate(assets):
        total = float(scores[asset].get("master_score") or 0)
        color = _sc(total)
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=round(total, 3),
            title={"text": f"<b>{asset}</b>", "font": {"color": TEXT, "size": 14}},
            number={"font": {"color": color, "size": 28}, "valueformat": ".3f"},
            gauge={
                "axis": {"range": [0, 1], "tickcolor": MUTED,
                          "tickfont": {"color": MUTED, "size": 9}},
                "bar":  {"color": color, "thickness": 0.22},
                "bgcolor": GRID,
                "borderwidth": 0,
                "steps": [
                    {"range": [0,                    cfg.BUY_THRESHOLD],  "color": "#0a2218"},
                    {"range": [cfg.BUY_THRESHOLD,    cfg.SELL_THRESHOLD], "color": "#1a1608"},
                    {"range": [cfg.SELL_THRESHOLD,   1],                  "color": "#200a10"},
                ],
                "threshold": {"line": {"color": color, "width": 2},
                              "thickness": 0.8, "value": total},
            },
        ), row=1, col=i+1)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color=TEXT,
        height=220, margin={"t": 40, "b": 10, "l": 10, "r": 10},
    )
    return fig


def subscores_fig(scores):
    assets = list(scores.keys())
    keys   = [("price_score","Price"),("pe_score","P/E"),
              ("vix_score","VIX"),("fx_score","FX (₹)")]
    fig = go.Figure()
    for key, label in keys:
        vals = [round(float(scores[a].get(key) or 0), 3) for a in assets]
        fig.add_trace(go.Bar(
            name=label, x=assets, y=vals,
            marker_color=SCORE_COLORS[key],
            marker_line_width=0,
            text=[f"{v:.2f}" for v in vals],
            textposition="outside",
            textfont={"color": TEXT, "size": 11},
        ))
    fig.add_hline(y=cfg.BUY_THRESHOLD,  line_dash="dot", line_color=BUY_C,  line_width=1.5)
    fig.add_hline(y=cfg.SELL_THRESHOLD, line_dash="dot", line_color=SELL_C, line_width=1.5)
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        yaxis={"range": [0, 1.25], "gridcolor": BORDER, "title": "Score",
                "tickfont": {"size": 10}},
        xaxis={"tickfont": {"size": 12}},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"size": 11}},
        height=320, margin={"t": 20, "b": 30, "l": 40, "r": 10},
    )
    return fig


def range_fig(asset_data):
    assets = [a for a in asset_data if a != "macro"]
    fig = go.Figure()
    for asset in assets:
        d    = asset_data[asset]
        curr = float(d.get("price")   or 0)
        low  = float(d.get("low_52w") or 0)
        high = float(d.get("high_52w")or 0)
        if high <= low or curr == 0: continue
        pct   = max(0.0, min(1.0, (curr - low)/(high - low)))
        color = _sc(pct)
        fig.add_trace(go.Bar(x=[100], base=[0], y=[asset], orientation="h",
                             marker_color=GRID, showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Bar(x=[cfg.BUY_THRESHOLD*100], base=[0], y=[asset],
                             orientation="h", marker_color="#0a2218",
                             showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Bar(x=[100-cfg.SELL_THRESHOLD*100],
                             base=[cfg.SELL_THRESHOLD*100], y=[asset],
                             orientation="h", marker_color="#200a10",
                             showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=[pct*100], y=[asset], mode="markers+text",
            marker={"size": 13, "color": color, "symbol": "diamond",
                    "line": {"color": TEXT, "width": 1}},
            text=[f"  ₹{curr:,.0f}"], textposition="middle right",
            textfont={"color": color, "size": 10}, showlegend=False,
            hovertemplate=f"<b>{asset}</b><br>₹{curr:,.2f} ({pct:.1%})<br>"
                          f"52W: ₹{low:,.0f} – ₹{high:,.0f}<extra></extra>",
        ))
        fig.add_annotation(x=0,   y=asset, text=f"₹{low:,.0f}", showarrow=False,
                           xanchor="right", xshift=-4, font={"color": BUY_C, "size": 9})
        fig.add_annotation(x=100, y=asset, text=f"₹{high:,.0f}", showarrow=False,
                           xanchor="left",  xshift=4,  font={"color": SELL_C, "size": 9})
    fig.add_vline(x=cfg.BUY_THRESHOLD*100,  line_dash="dot", line_color=BUY_C,  line_width=1)
    fig.add_vline(x=cfg.SELL_THRESHOLD*100, line_dash="dot", line_color=SELL_C, line_width=1)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        xaxis={"range": [-5, 145], "gridcolor": BORDER, "ticksuffix": "%",
                "title": "Position in 52W Range", "tickfont": {"size": 10}},
        yaxis={"autorange": "reversed", "tickfont": {"size": 12}},
        height=280, barmode="overlay",
        margin={"t": 20, "b": 40, "l": 80, "r": 20},
    )
    return fig


def macro_fig(macro):
    fig = make_subplots(rows=1, cols=2,
                        specs=[[{"type":"indicator"},{"type":"indicator"}]],
                        subplot_titles=["India VIX", "USD / INR (₹)"])
    panels = [
        ("vix",    cfg.VIX_MIN,    cfg.VIX_MAX,    True,  1),
        ("usdinr", cfg.USDINR_MIN, cfg.USDINR_MAX, True,  2),
    ]
    for key, vmin, vmax, inv, col in panels:
        curr  = float(macro.get(key) or 0)
        norm  = max(0.0, min(1.0, (curr-vmin)/(vmax-vmin) if vmax!=vmin else 0.5))
        color = _sc(1-norm if inv else norm)
        fig.add_trace(go.Indicator(
            mode="number+gauge+delta",
            value=round(curr, 2),
            delta={"reference": round((vmin+vmax)/2, 2), "valueformat": ".2f",
                   "increasing": {"color": SELL_C}, "decreasing": {"color": BUY_C}},
            number={"font": {"color": color, "size": 30}},
            gauge={
                "axis": {"range": [vmin, vmax], "tickcolor": MUTED,
                          "tickfont": {"color": MUTED}},
                "bar":  {"color": color, "thickness": 0.22},
                "bgcolor": GRID, "borderwidth": 0,
                "steps": [
                    {"range": [vmin, vmin+(vmax-vmin)*cfg.BUY_THRESHOLD],  "color": "#0a2218"},
                    {"range": [vmin+(vmax-vmin)*cfg.BUY_THRESHOLD,
                               vmin+(vmax-vmin)*cfg.SELL_THRESHOLD],        "color": "#1a1608"},
                    {"range": [vmin+(vmax-vmin)*cfg.SELL_THRESHOLD, vmax],  "color": "#200a10"},
                ],
            },
        ), row=1, col=col)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color=TEXT,
        height=230, margin={"t": 50, "b": 10},
    )
    for ann in fig.layout.annotations:
        ann.font.color = TEXT
        ann.font.size  = 13
    return fig


# ── Scores table ────────────────────────────────────────────────────────────
def scores_table(scores):
    rows = []
    for asset, s in scores.items():
        sig    = s.get("signal", "N/A")
        master = s.get("master_score") or 0
        rsi    = s.get("rsi")
        sbuy   = s.get("strong_buy", False)

        # Signal with strong buy override
        display_sig = "★ STRONG BUY" if sbuy else sig

        rows.append({
            "Asset":        asset,
            "Price (₹)":    f"₹{s.get('price') or 0:,.2f}",
            "52W High":     f"₹{s.get('high_52w') or 0:,.2f}",
            "52W Low":      f"₹{s.get('low_52w') or 0:,.2f}",
            "Price Score":  f"{s.get('price_score') or 0:.3f}",
            "P/E":          f"{s.get('pe'):.1f}" if s.get('pe') else "N/A",
            "VIX Score":    f"{s.get('vix_score') or 0:.3f}",
            "FX Score (₹)": f"{s.get('fx_score') or 0:.3f}",
            "RSI (Daily)":  f"{rsi:.1f}" if rsi is not None else "N/A",
            "Master Score": f"{master:.3f}",
            "Signal":       display_sig,
        })

    df = pd.DataFrame(rows)

    style_data_conditional = []
    for i, (asset, s) in enumerate(scores.items()):
        sig   = s.get("signal", "HOLD")
        sbuy  = s.get("strong_buy", False)
        rsi   = s.get("rsi")
        color = (SBUY_C if sbuy else
                 BUY_C  if sig == "BUY"  else
                 SELL_C if sig == "SELL" else HOLD_C)
        style_data_conditional.append({
            "if": {"row_index": i, "column_id": "Signal"},
            "color": color, "fontWeight": "bold",
        })
        style_data_conditional.append({
            "if": {"row_index": i, "column_id": "Master Score"},
            "color": _sc(s.get("master_score") or 0),
        })
        # RSI colour
        if rsi is not None:
            rsi_color = BUY_C if rsi < 30 else (SELL_C if rsi > 70 else TEXT)
            style_data_conditional.append({
                "if": {"row_index": i, "column_id": "RSI (Daily)"},
                "color": rsi_color, "fontWeight": "bold" if rsi < 30 else "normal",
            })

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": BORDER,
            "color": ACCENT,
            "fontWeight": "700",
            "fontSize": "11px",
            "textTransform": "uppercase",
            "letterSpacing": "0.08em",
            "border": f"1px solid {BORDER}",
            "fontFamily": "'DM Mono', monospace",
            "padding": "10px 14px",
        },
        style_data={
            "backgroundColor": CARD,
            "color": TEXT,
            "border": f"1px solid {BORDER}",
            "fontSize": "13px",
            "fontFamily": "'DM Mono', monospace",
            "padding": "10px 14px",
        },
        style_data_conditional=style_data_conditional,
        export_format="csv",       # ← download button
        export_headers="display",
        style_cell={"textAlign": "center", "minWidth": "100px"},
        style_cell_conditional=[
            {"if": {"column_id": "Asset"}, "textAlign": "left", "fontWeight": "600"},
        ],
    )


# ── Signal cards ────────────────────────────────────────────────────────────
def signal_cards(scores):
    cards = []
    for asset, s in scores.items():
        sig   = s.get("signal", "N/A")
        score = float(s.get("master_score") or 0)
        price = s.get("price") or 0
        rsi   = s.get("rsi")
        sbuy  = s.get("strong_buy", False)

        display = "★ STRONG BUY" if sbuy else sig
        color   = SBUY_C if sbuy else _sc(score)
        bg_map  = {"BUY": "#081a12", "SELL": "#18060c", "HOLD": "#14100a"}
        bg      = "#030d08" if sbuy else bg_map.get(sig, CARD)

        rsi_el = html.Div([
            html.Span("RSI ", style={"color": MUTED, "fontSize": "11px"}),
            html.Span(
                f"{rsi:.0f}" if rsi else "—",
                style={"color": BUY_C if (rsi and rsi < 30) else
                               (SELL_C if (rsi and rsi > 70) else TEXT),
                       "fontWeight": "700", "fontSize": "13px"}
            ),
        ], style={"marginTop": "6px"})

        cards.append(html.Div([
            html.Div(asset, style={
                "fontSize": "11px", "color": MUTED,
                "letterSpacing": "0.1em", "textTransform": "uppercase",
                "marginBottom": "6px", "fontFamily": "'DM Mono', monospace",
            }),
            html.Div(f"{_sig_icon(display)} {display}", style={
                "fontSize": "16px", "fontWeight": "800", "color": color,
                "letterSpacing": "0.05em",
            }),
            html.Div(f"{score:.3f}", style={
                "fontSize": "28px", "fontWeight": "900", "color": color,
                "lineHeight": "1.1", "marginTop": "4px",
                "fontFamily": "'DM Mono', monospace",
            }),
            html.Div(f"₹{price:,.2f}", style={
                "fontSize": "12px", "color": MUTED, "marginTop": "2px",
                "fontFamily": "'DM Mono', monospace",
            }),
            rsi_el,
            # Thin colour bar at bottom
            html.Div(style={
                "position": "absolute", "bottom": "0", "left": "0", "right": "0",
                "height": "3px", "background": color, "borderRadius": "0 0 10px 10px",
            }),
        ], style={
            "background": bg,
            "border": f"1px solid {color}33",
            "borderRadius": "10px",
            "padding": "18px 20px 20px",
            "minWidth": "155px",
            "flex": "1",
            "position": "relative",
            "overflow": "hidden",
        }))
    return cards


# ── Section wrapper ─────────────────────────────────────────────────────────
def section(title, content, right=None):
    return html.Div([
        html.Div([
            html.Span(title, style={
                "fontSize": "11px", "color": ACCENT,
                "letterSpacing": "0.15em", "textTransform": "uppercase",
                "fontWeight": "700", "fontFamily": "'DM Mono', monospace",
            }),
            html.Span(right or "", style={"fontSize": "11px", "color": MUTED}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "14px", "paddingBottom": "10px",
                  "borderBottom": f"1px solid {BORDER}"}),
        content,
    ], style={
        "background": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "padding": "20px",
        "marginBottom": "16px",
    })


# ── App ─────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    title="Quant India",
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@600;700;800&display=swap"
    ],
)

app.layout = html.Div([
    dcc.Interval(id="tick", interval=cfg.REFRESH_SEC * 1000, n_intervals=0),

    # ── Top bar ──────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Span("QUANT", style={
                "fontSize": "22px", "fontWeight": "800", "color": ACCENT,
                "fontFamily": "'Syne', sans-serif", "letterSpacing": "0.08em",
            }),
            html.Span(" INDIA", style={
                "fontSize": "22px", "fontWeight": "800", "color": TEXT,
                "fontFamily": "'Syne', sans-serif",
            }),
            html.Span(" / LIVE DASHBOARD", style={
                "fontSize": "12px", "color": MUTED, "marginLeft": "14px",
                "letterSpacing": "0.12em", "fontFamily": "'DM Mono', monospace",
                "verticalAlign": "middle",
            }),
        ]),
        html.Div([
            html.Span("●", style={"color": BUY_C, "fontSize": "10px", "marginRight": "6px"}),
            html.Span(id="ts", style={
                "fontSize": "12px", "color": MUTED,
                "fontFamily": "'DM Mono', monospace",
            }),
            html.Span(f"  REFRESH/{cfg.REFRESH_SEC}s", style={
                "fontSize": "11px", "color": BORDER, "marginLeft": "10px",
                "fontFamily": "'DM Mono', monospace",
            }),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={
        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
        "padding": "16px 28px", "borderBottom": f"1px solid {BORDER}",
        "background": SURFACE,
        "position": "sticky", "top": "0", "zIndex": "100",
    }),

    # ── Body ─────────────────────────────────────────────────────────────
    html.Div([

        # Signal cards
        html.Div(id="cards", style={
            "display": "flex", "gap": "14px", "marginBottom": "16px", "flexWrap": "wrap",
        }),

        # Gauges
        section("Master Score Gauges",
                dcc.Graph(id="gauges", config={"displayModeBar": False})),

        # Sub-scores + Range
        html.Div([
            html.Div(
                section("Sub-Score Breakdown",
                        dcc.Graph(id="subscores", config={"displayModeBar": False})),
                style={"flex": "1", "minWidth": "0"}
            ),
            html.Div(
                section("52-Week Range Position",
                        dcc.Graph(id="range", config={"displayModeBar": False})),
                style={"flex": "1", "minWidth": "0"}
            ),
        ], style={"display": "flex", "gap": "16px"}),

        # Macro
        section("Macro — India VIX  &  USD/INR (₹)",
                dcc.Graph(id="macro", config={"displayModeBar": False})),

        # Scores table with download
        section(
            "Full Scores Table",
            html.Div(id="table"),
            right="⬇ CSV download available →",
        ),

        # Legend
        html.Div([
            *[html.Span([
                html.Span("█ ", style={"color": c}),
                html.Span(t, style={"color": MUTED, "marginRight": "24px",
                                    "fontFamily": "'DM Mono', monospace",
                                    "fontSize": "11px"}),
            ]) for c, t in [
                (SBUY_C, "★ STRONG BUY (RSI<30 & Score<0.35)"),
                (BUY_C,  "BUY  Score < 0.35"),
                (HOLD_C, "HOLD  0.35 – 0.65"),
                (SELL_C, "SELL  Score > 0.65"),
            ]],
        ], style={"padding": "12px 0 24px", "textAlign": "center"}),

    ], style={"padding": "20px 28px", "maxWidth": "1600px", "margin": "0 auto"}),

], style={
    "background": BG,
    "minHeight": "100vh",
    "fontFamily": "'DM Mono', monospace",
    "color": TEXT,
})


# ── Callback ─────────────────────────────────────────────────────────────────
@app.callback(
    Output("ts",        "children"),
    Output("cards",     "children"),
    Output("gauges",    "figure"),
    Output("subscores", "figure"),
    Output("range",     "figure"),
    Output("macro",     "figure"),
    Output("table",     "children"),
    Input("tick", "n_intervals"),
)
def refresh(_):
    scores, asset_data, macro = get_data()

    if not scores:
        empty = go.Figure()
        empty.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                            font_color=TEXT, title="No data — check logs")
        msg = "Fetch failed"
        return msg, [], empty, empty, empty, empty, html.Div("No data")

    ts = datetime.now().strftime("%d %b %Y  %H:%M:%S")

    return (
        ts,
        signal_cards(scores),
        gauges_fig(scores),
        subscores_fig(scores),
        range_fig(asset_data),
        macro_fig(macro),
        scores_table(scores),
    )


if __name__ == "__main__":
    print("\n" + "═"*52)
    print("  🚀  Quant India Dashboard")
    print("  ➜   http://127.0.0.1:8050")
    print(f"  ⟳   Auto-refresh every {cfg.REFRESH_SEC}s")
    print("  ✕   Ctrl+C to stop")
    print("═"*52 + "\n")
    app.run(debug=False, host="127.0.0.1", port=8050)