"""
streamlit_app.py — Professional Quant India Live Dashboard
===========================================================
Deploy on Streamlit Cloud. Reads scores.json from GitHub.
"""

import json
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quant India — Live Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Config (must match your config.py) ─────────────────────────────────────
GITHUB_RAW_URL = st.secrets.get(
    "GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/scores.json"
)
BUY_THRESHOLD  = 0.35
SELL_THRESHOLD = 0.65
REFRESH_SEC    = 60

# ── Colour palette ──────────────────────────────────────────────────────────
BG      = "#070d14"
SURFACE = "#0e1621"
CARD    = "#131f2e"
BORDER  = "#1e2d3d"
ACCENT  = "#00d4ff"
BUY_C   = "#00e5a0"
HOLD_C  = "#f59e0b"
SELL_C  = "#f43f5e"
SBUY_C  = "#00ff88"
TEXT    = "#e2eaf5"
MUTED   = "#5a7a9a"
GRID    = "#111c28"

ASSET_COLORS = {
    "Nifty":    "#00d4ff",
    "Infosys":  "#00e5a0",
    "Reliance": "#f59e0b",
    "ICICI":    "#c084fc",
}

SCORE_COLORS = {
    "price_score": "#00d4ff",
    "pe_score":    "#00e5a0",
    "vix_score":   "#f59e0b",
    "fx_score":    "#c084fc",
}

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@600;700;800;900&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'DM Mono', monospace !important;
    background-color: #070d14 !important;
    color: #e2eaf5 !important;
}
.stApp { background-color: #070d14 !important; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; padding-bottom: 0 !important; }

/* Top header bar */
.top-bar {
    background: linear-gradient(135deg, #0e1621 0%, #131f2e 100%);
    border: 1px solid #1e2d3d;
    border-radius: 14px;
    padding: 18px 28px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.logo-text {
    font-family: 'Syne', sans-serif !important;
    font-size: 26px;
    font-weight: 900;
    letter-spacing: 0.06em;
}
.logo-quant { color: #00d4ff; }
.logo-india { color: #e2eaf5; }
.live-badge {
    background: #00e5a020;
    border: 1px solid #00e5a050;
    color: #00e5a0;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    letter-spacing: 0.1em;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.6; }
}

/* Signal cards */
.sig-card {
    background: linear-gradient(145deg, #0e1a28, #131f2e);
    border-radius: 14px;
    padding: 20px 22px 22px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s;
}
.sig-card:hover { transform: translateY(-2px); }
.sig-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 14px 14px 0 0;
}
.card-asset {
    font-size: 10px;
    color: #5a7a9a;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.card-signal {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.08em;
    margin-bottom: 2px;
}
.card-score {
    font-family: 'Syne', sans-serif !important;
    font-size: 36px;
    font-weight: 900;
    line-height: 1;
    margin: 6px 0 4px;
}
.card-price {
    font-size: 12px;
    color: #5a7a9a;
    margin-bottom: 8px;
}
.card-rsi {
    font-size: 11px;
    color: #5a7a9a;
}
.card-rsi span { font-weight: 700; font-size: 13px; }

/* Section headers */
.section-header {
    font-size: 10px;
    font-weight: 700;
    color: #00d4ff;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e2d3d;
    margin-bottom: 14px;
}

/* Metric boxes */
.metric-box {
    background: #0e1621;
    border: 1px solid #1e2d3d;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.metric-label {
    font-size: 10px;
    color: #5a7a9a;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'Syne', sans-serif !important;
    font-size: 24px;
    font-weight: 800;
}

/* Timestamp */
.ts-bar {
    background: #0e1621;
    border: 1px solid #1e2d3d;
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 11px;
    color: #5a7a9a;
    text-align: center;
    margin-bottom: 16px;
    letter-spacing: 0.05em;
}
.ts-dot { color: #00e5a0; margin-right: 6px; }

/* Legend */
.legend-bar {
    background: #0e1621;
    border: 1px solid #1e2d3d;
    border-radius: 10px;
    padding: 12px 20px;
    margin-top: 8px;
    font-size: 11px;
    color: #5a7a9a;
    text-align: center;
    letter-spacing: 0.04em;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0e1621; }
::-webkit-scrollbar-thumb { background: #1e2d3d; border-radius: 4px; }

/* Table */
.dataframe { font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ── Data loader ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_SEC)
def load_scores():
    try:
        r = requests.get(GITHUB_RAW_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return None


def sig_color(score):
    if score is None: return MUTED
    if score < BUY_THRESHOLD:  return BUY_C
    if score > SELL_THRESHOLD: return SELL_C
    return HOLD_C


def sig_label(score, strong_buy=False):
    if strong_buy: return "★ STRONG BUY"
    if score is None: return "N/A"
    if score < BUY_THRESHOLD:  return "▲ BUY"
    if score > SELL_THRESHOLD: return "▼ SELL"
    return "● HOLD"


# ── Chart builders ──────────────────────────────────────────────────────────

def make_gauge_fig(scores):
    assets = [k for k in scores if k != "macro"]
    n = len(assets)
    fig = make_subplots(
        rows=1, cols=n,
        specs=[[{"type": "indicator"}] * n],
        horizontal_spacing=0.05,
    )
    for i, asset in enumerate(assets):
        s     = scores[asset]
        total = float(s.get("master_score") or 0)
        color = sig_color(total)
        sbuy  = s.get("strong_buy", False)
        if sbuy: color = SBUY_C

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=round(total, 3),
            title={"text": f"<b>{asset}</b>", "font": {"color": TEXT, "size": 13}},
            number={"font": {"color": color, "size": 30}, "valueformat": ".3f"},
            gauge={
                "axis": {"range": [0, 1], "tickcolor": MUTED,
                          "tickfont": {"color": MUTED, "size": 9},
                          "nticks": 6},
                "bar":  {"color": color, "thickness": 0.2},
                "bgcolor": "#0a1520",
                "borderwidth": 1,
                "bordercolor": BORDER,
                "steps": [
                    {"range": [0,              BUY_THRESHOLD],  "color": "#071510"},
                    {"range": [BUY_THRESHOLD,  SELL_THRESHOLD], "color": "#0f1008"},
                    {"range": [SELL_THRESHOLD, 1],              "color": "#150508"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 2},
                    "thickness": 0.85, "value": total,
                },
            },
        ), row=1, col=i + 1)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        height=240,
        margin={"t": 50, "b": 10, "l": 20, "r": 20},
    )
    return fig


def make_subscore_fig(scores):
    assets = [k for k in scores if k != "macro"]
    comps  = [
        ("price_score", "Price"),
        ("pe_score",    "P/E"),
        ("vix_score",   "VIX"),
        ("fx_score",    "FX (₹)"),
    ]
    fig = go.Figure()
    for key, label in comps:
        vals = [round(float(scores[a].get(key) or 0), 3) for a in assets]
        fig.add_trace(go.Bar(
            name=label, x=assets, y=vals,
            marker_color=SCORE_COLORS[key],
            marker_line_width=0,
            text=[f"{v:.2f}" for v in vals],
            textposition="outside",
            textfont={"color": TEXT, "size": 10},
        ))

    fig.add_hrect(y0=0, y1=BUY_THRESHOLD,
                  fillcolor=BUY_C, opacity=0.04, line_width=0)
    fig.add_hrect(y0=SELL_THRESHOLD, y1=1.3,
                  fillcolor=SELL_C, opacity=0.04, line_width=0)
    fig.add_hline(y=BUY_THRESHOLD,  line_dash="dot",
                  line_color=BUY_C,  line_width=1.5,
                  annotation_text="BUY zone",
                  annotation_font_color=BUY_C, annotation_font_size=10)
    fig.add_hline(y=SELL_THRESHOLD, line_dash="dot",
                  line_color=SELL_C, line_width=1.5,
                  annotation_text="SELL zone",
                  annotation_font_color=SELL_C, annotation_font_size=10)

    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        yaxis={"range": [0, 1.3], "gridcolor": "#0e1a28",
                "title": "Score (0–1)", "tickfont": {"size": 10}},
        xaxis={"tickfont": {"size": 12}},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"size": 11},
                "orientation": "h", "yanchor": "bottom", "y": 1.02,
                "xanchor": "right", "x": 1},
        height=340,
        margin={"t": 40, "b": 20, "l": 50, "r": 20},
    )
    return fig


def make_range_fig(scores):
    assets = [k for k in scores if k != "macro"]
    fig = go.Figure()

    for asset in assets:
        s    = scores[asset]
        curr = float(s.get("price")    or 0)
        low  = float(s.get("low_52w")  or 0)
        high = float(s.get("high_52w") or 0)
        if high <= low or curr == 0:
            continue
        pct   = max(0.0, min(1.0, (curr - low) / (high - low)))
        color = SBUY_C if s.get("strong_buy") else sig_color(pct)

        # Background bar
        fig.add_trace(go.Bar(
            x=[100], base=[0], y=[asset], orientation="h",
            marker_color="#0a1520", marker_line_width=0,
            showlegend=False, hoverinfo="skip",
        ))
        # BUY zone
        fig.add_trace(go.Bar(
            x=[BUY_THRESHOLD * 100], base=[0], y=[asset], orientation="h",
            marker_color="#071510", marker_line_width=0,
            showlegend=False, hoverinfo="skip",
        ))
        # SELL zone
        fig.add_trace(go.Bar(
            x=[100 - SELL_THRESHOLD * 100],
            base=[SELL_THRESHOLD * 100], y=[asset], orientation="h",
            marker_color="#150508", marker_line_width=0,
            showlegend=False, hoverinfo="skip",
        ))
        # Current price marker
        fig.add_trace(go.Scatter(
            x=[pct * 100], y=[asset],
            mode="markers+text",
            marker={"size": 14, "color": color, "symbol": "diamond",
                    "line": {"color": "#e2eaf5", "width": 1}},
            text=[f"  ₹{curr:,.0f}"],
            textposition="middle right",
            textfont={"color": color, "size": 11},
            showlegend=False,
            hovertemplate=(
                f"<b>{asset}</b><br>"
                f"Price  : ₹{curr:,.2f}<br>"
                f"52W Low: ₹{low:,.2f}<br>"
                f"52W Hi : ₹{high:,.2f}<br>"
                f"Pos    : {pct:.1%}<extra></extra>"
            ),
        ))
        fig.add_annotation(
            x=0,   y=asset, text=f"₹{low:,.0f}",
            showarrow=False, xanchor="right", xshift=-6,
            font={"color": BUY_C, "size": 9},
        )
        fig.add_annotation(
            x=100, y=asset, text=f"₹{high:,.0f}",
            showarrow=False, xanchor="left", xshift=6,
            font={"color": SELL_C, "size": 9},
        )

    fig.add_vline(x=BUY_THRESHOLD  * 100, line_dash="dot",
                  line_color=BUY_C,  line_width=1.2)
    fig.add_vline(x=SELL_THRESHOLD * 100, line_dash="dot",
                  line_color=SELL_C, line_width=1.2)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        xaxis={"range": [-8, 150], "gridcolor": "#0e1a28",
                "ticksuffix": "%", "title": "Position in 52-Week Range",
                "tickfont": {"size": 10}},
        yaxis={"autorange": "reversed", "tickfont": {"size": 12}},
        height=300,
        barmode="overlay",
        margin={"t": 10, "b": 40, "l": 80, "r": 30},
    )
    return fig


def make_macro_fig(macro):
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=["India VIX", "USD / INR  (₹)"],
    )
    VIX_MIN, VIX_MAX     = 10.0, 35.0
    FX_MIN,  FX_MAX      = 70.0, 96.0

    panels = [
        ("vix",    VIX_MIN, VIX_MAX, True,  1),
        ("usdinr", FX_MIN,  FX_MAX,  True,  2),
    ]
    for key, vmin, vmax, inv, col in panels:
        curr  = float(macro.get(key) or 0)
        norm  = max(0.0, min(1.0, (curr - vmin) / (vmax - vmin) if vmax != vmin else 0.5))
        color = sig_color(1 - norm if inv else norm)

        fig.add_trace(go.Indicator(
            mode="number+gauge+delta",
            value=round(curr, 2),
            delta={
                "reference":   round((vmin + vmax) / 2, 2),
                "valueformat": ".2f",
                "increasing":  {"color": SELL_C},
                "decreasing":  {"color": BUY_C},
            },
            number={"font": {"color": color, "size": 34}},
            gauge={
                "axis": {"range": [vmin, vmax], "tickcolor": MUTED,
                          "tickfont": {"color": MUTED, "size": 9}},
                "bar":  {"color": color, "thickness": 0.2},
                "bgcolor": "#0a1520",
                "borderwidth": 1,
                "bordercolor": BORDER,
                "steps": [
                    {"range": [vmin, vmin + (vmax - vmin) * BUY_THRESHOLD],                           "color": "#071510"},
                    {"range": [vmin + (vmax - vmin) * BUY_THRESHOLD, vmin + (vmax - vmin) * SELL_THRESHOLD], "color": "#0f1008"},
                    {"range": [vmin + (vmax - vmin) * SELL_THRESHOLD, vmax],                          "color": "#150508"},
                ],
            },
        ), row=1, col=col)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        height=260,
        margin={"t": 60, "b": 10, "l": 20, "r": 20},
    )
    for ann in fig.layout.annotations:
        ann.font.color = TEXT
        ann.font.size  = 13
    return fig


def make_master_trend_fig(scores):
    """Horizontal bar chart comparing all master scores."""
    assets = [k for k in scores if k != "macro"]
    vals   = [float(scores[a].get("master_score") or 0) for a in assets]
    colors = [SBUY_C if scores[a].get("strong_buy") else sig_color(v)
              for a, v in zip(assets, vals)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=vals, y=assets, orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=[f"{v:.3f}" for v in vals],
        textposition="outside",
        textfont={"color": TEXT, "size": 12},
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>",
    ))
    fig.add_vline(x=BUY_THRESHOLD,  line_dash="dot",
                  line_color=BUY_C,  line_width=1.5,
                  annotation_text="BUY",
                  annotation_font_color=BUY_C, annotation_font_size=10)
    fig.add_vline(x=SELL_THRESHOLD, line_dash="dot",
                  line_color=SELL_C, line_width=1.5,
                  annotation_text="SELL",
                  annotation_font_color=SELL_C, annotation_font_size=10)
    fig.add_vrect(x0=0, x1=BUY_THRESHOLD,
                  fillcolor=BUY_C, opacity=0.05, line_width=0)
    fig.add_vrect(x0=SELL_THRESHOLD, x1=1,
                  fillcolor=SELL_C, opacity=0.05, line_width=0)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        xaxis={"range": [0, 1.15], "gridcolor": "#0e1a28",
                "title": "Master Score", "tickfont": {"size": 10}},
        yaxis={"tickfont": {"size": 13}, "autorange": "reversed"},
        height=240,
        margin={"t": 10, "b": 30, "l": 80, "r": 60},
    )
    return fig


# ── Scores DataFrame ────────────────────────────────────────────────────────

def make_scores_df(scores):
    rows = []
    for asset, s in scores.items():
        if asset == "macro":
            continue
        sbuy = s.get("strong_buy", False)
        sig  = "★ STRONG BUY" if sbuy else s.get("signal", "N/A")
        rsi  = s.get("rsi")
        rows.append({
            "Asset":        asset,
            "Price (₹)":    f"₹{float(s.get('price') or 0):,.2f}",
            "52W High":     f"₹{float(s.get('high_52w') or 0):,.2f}",
            "52W Low":      f"₹{float(s.get('low_52w') or 0):,.2f}",
            "Price Score":  round(float(s.get("price_score") or 0), 3),
            "P/E":          f"{s.get('pe'):.1f}" if s.get("pe") else "N/A",
            "VIX Score":    round(float(s.get("vix_score") or 0), 3),
            "FX Score":     round(float(s.get("fx_score") or 0), 3),
            "RSI (Daily)":  f"{rsi:.1f}" if rsi is not None else "N/A",
            "Master Score": round(float(s.get("master_score") or 0), 3),
            "Signal":       sig,
        })
    return pd.DataFrame(rows)


# ── Main layout ─────────────────────────────────────────────────────────────

def main():
    # Auto-refresh
    st_autorefresh = st.empty()

    # Load data
    data = load_scores()

    if data is None:
        st.error("⚠ Could not load scores. Check your GitHub URL in secrets.")
        st.stop()

    scores    = {k: v for k, v in data.items() if k != "meta"}
    macro     = scores.pop("macro", {})
    meta      = data.get("meta", {})
    updated   = meta.get("updated_at", "Unknown")
    cycle     = meta.get("cycle", "—")

    # ── Top bar ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="top-bar">
        <div>
            <span class="logo-text">
                <span class="logo-quant">QUANT</span>
                <span class="logo-india"> INDIA</span>
            </span>
            <span style="font-size:11px; color:#5a7a9a; margin-left:16px;
                         letter-spacing:0.1em; font-family:'DM Mono',monospace;">
                / LIVE SCORING DASHBOARD
            </span>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
            <span class="live-badge">● LIVE</span>
            <span style="font-size:11px; color:#5a7a9a; font-family:'DM Mono',monospace;">
                Cycle #{cycle}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Timestamp bar ─────────────────────────────────────────────────────
    now_local = datetime.now().strftime("%d %b %Y  %H:%M:%S")
    st.markdown(f"""
    <div class="ts-bar">
        <span class="ts-dot">●</span>
        Data updated at <b style="color:#e2eaf5">{updated}</b>
        &nbsp;·&nbsp; Dashboard refreshed at <b style="color:#e2eaf5">{now_local}</b>
        &nbsp;·&nbsp; Auto-refresh every <b style="color:#e2eaf5">{REFRESH_SEC}s</b>
    </div>
    """, unsafe_allow_html=True)

    # ── Signal cards ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">SIGNALS AT A GLANCE</div>',
                unsafe_allow_html=True)

    asset_keys = list(scores.keys())
    cols = st.columns(len(asset_keys))

    for col, asset in zip(cols, asset_keys):
        s     = scores[asset]
        score = float(s.get("master_score") or 0)
        sbuy  = s.get("strong_buy", False)
        sig   = sig_label(score, sbuy)
        color = SBUY_C if sbuy else sig_color(score)
        price = float(s.get("price") or 0)
        rsi   = s.get("rsi")

        rsi_color = (BUY_C  if rsi and rsi < 30 else
                     SELL_C if rsi and rsi > 70 else TEXT)
        rsi_str = f"{rsi:.0f}" if rsi is not None else "—"

        with col:
            st.markdown(f"""
            <div class="sig-card" style="border:1px solid {color}25; background:linear-gradient(145deg,#0a1520,#131f2e);">
                <div style="position:absolute;top:0;left:0;right:0;height:3px;
                             background:{color};border-radius:14px 14px 0 0;"></div>
                <div class="card-asset">{asset}</div>
                <div class="card-signal" style="color:{color}">{sig}</div>
                <div class="card-score" style="color:{color}">{score:.3f}</div>
                <div class="card-price">₹{price:,.2f}</div>
                <div class="card-rsi">RSI &nbsp;<span style="color:{rsi_color}">{rsi_str}</span></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Macro metrics ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">MACRO INDICATORS</div>',
                unsafe_allow_html=True)

    vix    = float(macro.get("vix")    or 0)
    usdinr = float(macro.get("usdinr") or 0)
    vs     = float(macro.get("vix_score")    or 0)
    fs     = float(macro.get("fx_score")     or 0)

    m1, m2, m3, m4 = st.columns(4)
    for col, label, val, extra in [
        (m1, "India VIX",     f"{vix:.2f}",    f"Score: {vs:.3f}"),
        (m2, "USD / INR (₹)", f"₹{usdinr:.2f}", f"Score: {fs:.3f}"),
        (m3, "VIX Signal",    "FEAR" if vix > 20 else "CALM",
             "High fear = opportunity" if vix > 20 else "Low volatility"),
        (m4, "FX Signal",
             "WEAK ₹" if usdinr > 85 else "STABLE ₹",
             "Bearish for equities" if usdinr > 85 else "Neutral/Bullish"),
    ]:
        with col:
            vcolor = (SELL_C if vix > 25 else BUY_C if vix < 15 else HOLD_C)
            fcolor = (SELL_C if usdinr > 85 else BUY_C)
            c = vcolor if "VIX" in label or "Fear" in label.upper() else (
                fcolor if "INR" in label or "FX" in label else TEXT)
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{c}">{val}</div>
                <div style="font-size:10px;color:#5a7a9a;margin-top:4px">{extra}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Master score gauges ────────────────────────────────────────────────
    st.markdown('<div class="section-header">MASTER SCORE GAUGES</div>',
                unsafe_allow_html=True)
    st.plotly_chart(make_gauge_fig(scores), use_container_width=True,
                    config={"displayModeBar": False})

    # ── Master score comparison + 52W range ──────────────────────────────
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="section-header">MASTER SCORE COMPARISON</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(make_master_trend_fig(scores),
                        use_container_width=True,
                        config={"displayModeBar": False})
    with c2:
        st.markdown('<div class="section-header">52-WEEK RANGE POSITION</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(make_range_fig(scores),
                        use_container_width=True,
                        config={"displayModeBar": False})

    # ── Sub-scores + Macro ────────────────────────────────────────────────
    c3, c4 = st.columns([3, 2])
    with c3:
        st.markdown('<div class="section-header">SUB-SCORE BREAKDOWN</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(make_subscore_fig(scores),
                        use_container_width=True,
                        config={"displayModeBar": False})
    with c4:
        st.markdown('<div class="section-header">MACRO PANEL</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(make_macro_fig(macro),
                        use_container_width=True,
                        config={"displayModeBar": False})

    # ── Full scores table ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">FULL SCORES TABLE  —  ⬇ Download CSV below</div>',
                unsafe_allow_html=True)
    df = make_scores_df(scores)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Master Score": st.column_config.ProgressColumn(
                "Master Score", min_value=0, max_value=1, format="%.3f"
            ),
            "Price Score": st.column_config.ProgressColumn(
                "Price Score", min_value=0, max_value=1, format="%.3f"
            ),
        },
    )
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Full Report (CSV)",
        data=csv,
        file_name=f"quant_india_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ── Legend ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="legend-bar">
        <span style="color:{SBUY_C}">★ STRONG BUY</span> &nbsp;RSI &lt; 30 &amp; Score &lt; 0.35
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:{BUY_C}">▲ BUY</span> &nbsp;Score &lt; 0.35
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:{HOLD_C}">● HOLD</span> &nbsp;0.35 – 0.65
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:{SELL_C}">▼ SELL</span> &nbsp;Score &gt; 0.65
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:#5a7a9a">Score = weighted avg of Price, P/E, VIX, FX (₹)</span>
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh using Streamlit rerun
    time.sleep(REFRESH_SEC)
    st.rerun()


if __name__ == "__main__":
    main()