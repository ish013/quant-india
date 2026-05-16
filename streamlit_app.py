"""
streamlit_app.py — Quant India  |  Investor Dashboard
======================================================
Clean, light, editorial UI designed for serious investors.
Aesthetic direction: WSJ/Bloomberg terminal meets Swiss grid design.
Typography: Playfair Display (headlines) + IBM Plex Mono (data)
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
    page_title="Quant India — Investor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Constants ──────────────────────────────────────────────────────────────
GITHUB_RAW_URL = st.secrets.get(
    "GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/scores.json"
)
BUY_THRESHOLD  = 0.35
SELL_THRESHOLD = 0.65
REFRESH_SEC    = 60

# ── Design tokens ──────────────────────────────────────────────────────────
# Light editorial palette — WSJ-inspired
C = {
    "bg":           "#F7F5F0",   # warm off-white
    "surface":      "#FFFFFF",
    "surface2":     "#FAFAF8",
    "border":       "#E4E0D8",
    "border_dark":  "#C8C2B5",
    "text":         "#1A1915",
    "text_muted":   "#6B6760",
    "text_light":   "#9B9690",
    "buy":          "#1B6B3A",   # deep forest green
    "buy_bg":       "#EBF5EE",
    "buy_border":   "#A8D5B5",
    "sell":         "#B82C2C",   # deep crimson
    "sell_bg":      "#FBF0F0",
    "sell_border":  "#E8A8A8",
    "hold":         "#8B6914",   # warm amber
    "hold_bg":      "#FDF6E3",
    "hold_border":  "#E8D48A",
    "sbuy":         "#0D4F7C",   # deep blue for strong buy
    "sbuy_bg":      "#E8F2FA",
    "accent":       "#1A1915",
    "grid":         "#F0EDE8",
    "chart_1":      "#2E5FA3",
    "chart_2":      "#1B6B3A",
    "chart_3":      "#B82C2C",
    "chart_4":      "#8B6914",
}

ASSET_CHART_COLORS = {
    "Nifty":     "#2E5FA3",
    "Infosys":   "#1B6B3A",
    "Reliance":  "#B82C2C",
    "ICICI Bank":"#8B6914",
}

COMPONENT_COLORS = {
    "price_score": "#2E5FA3",
    "pe_score":    "#1B6B3A",
    "vix_score":   "#8B6914",
    "fx_score":    "#6B4497",
}

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif !important;
    background-color: {C['bg']} !important;
    color: {C['text']} !important;
}}
.stApp {{ background-color: {C['bg']} !important; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
    padding: 2rem 2.5rem 1rem !important;
    max-width: 1400px !important;
}}

/* ── Masthead ── */
.masthead {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding-bottom: 16px;
    border-bottom: 2px solid {C['text']};
    margin-bottom: 8px;
}}
.masthead-title {{
    font-family: 'Playfair Display', serif !important;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: {C['text']};
    line-height: 1;
}}
.masthead-sub {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px;
    font-weight: 400;
    color: {C['text_muted']};
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 5px;
}}
.masthead-right {{
    text-align: right;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px;
    color: {C['text_muted']};
    line-height: 1.7;
}}
.live-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    background: {C['buy']};
    border-radius: 50%;
    margin-right: 5px;
    animation: blink 2s ease-in-out infinite;
}}
@keyframes blink {{
    0%,100% {{ opacity:1; }}
    50%      {{ opacity:0.3; }}
}}

/* ── Section label ── */
.section-label {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: {C['text_muted']};
    padding-bottom: 8px;
    border-bottom: 1px solid {C['border']};
    margin-bottom: 16px;
}}

/* ── Signal cards ── */
.sig-card {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 3px;
    padding: 20px 22px 18px;
    position: relative;
    transition: box-shadow 0.2s;
}}
.sig-card:hover {{
    box-shadow: 0 4px 20px rgba(26,25,21,0.08);
}}
.card-ticker {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: {C['text_muted']};
    margin-bottom: 10px;
}}
.card-price {{
    font-family: 'Playfair Display', serif !important;
    font-size: 26px;
    font-weight: 600;
    color: {C['text']};
    line-height: 1;
    margin-bottom: 4px;
}}
.card-score-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 12px 0 10px;
    padding: 10px 0;
    border-top: 1px solid {C['border']};
    border-bottom: 1px solid {C['border']};
}}
.card-score-val {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 28px;
    font-weight: 500;
    line-height: 1;
}}
.card-signal-pill {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    padding: 5px 10px;
    border-radius: 2px;
}}
.card-meta {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px;
    color: {C['text_muted']};
    display: flex;
    justify-content: space-between;
}}

/* ── Macro tiles ── */
.macro-tile {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 3px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
}}
.macro-label {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: {C['text_muted']};
    margin-bottom: 5px;
}}
.macro-value {{
    font-family: 'Playfair Display', serif !important;
    font-size: 28px;
    font-weight: 600;
    line-height: 1;
}}
.macro-sub {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px;
    color: {C['text_muted']};
    margin-top: 4px;
}}

/* ── Score bar component ── */
.score-bar-wrap {{
    margin-bottom: 14px;
}}
.score-bar-header {{
    display: flex;
    justify-content: space-between;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px;
    margin-bottom: 5px;
    color: {C['text']};
}}
.score-bar-header span:last-child {{ color: {C['text_muted']}; }}
.score-bar-track {{
    height: 6px;
    background: {C['grid']};
    border-radius: 1px;
    position: relative;
    overflow: visible;
}}
.score-bar-fill {{
    height: 100%;
    border-radius: 1px;
    transition: width 0.6s ease;
}}
.score-bar-buy-line {{
    position: absolute;
    top: -3px;
    bottom: -3px;
    width: 1px;
    background: {C['buy']};
    opacity: 0.4;
    left: 35%;
}}
.score-bar-sell-line {{
    position: absolute;
    top: -3px;
    bottom: -3px;
    width: 1px;
    background: {C['sell']};
    opacity: 0.4;
    left: 65%;
}}

/* ── Data table override ── */
.stDataFrame {{ border: 1px solid {C['border']} !important; border-radius: 3px !important; }}
.stDataFrame th {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    background: {C['surface2']} !important;
    color: {C['text_muted']} !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
    padding: 10px 14px !important;
    border-bottom: 1px solid {C['border']} !important;
}}
.stDataFrame td {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    padding: 9px 14px !important;
    border-bottom: 1px solid {C['border']} !important;
    color: {C['text']} !important;
}}

/* ── Divider ── */
.rule {{ height: 1px; background: {C['border']}; margin: 24px 0; }}
.rule-heavy {{ height: 2px; background: {C['text']}; margin: 24px 0; }}

/* ── Download button ── */
.stDownloadButton button {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.1em !important;
    background: {C['surface']} !important;
    color: {C['text']} !important;
    border: 1px solid {C['border_dark']} !important;
    border-radius: 2px !important;
    padding: 8px 18px !important;
    transition: all 0.15s !important;
}}
.stDownloadButton button:hover {{
    background: {C['text']} !important;
    color: {C['bg']} !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 1px solid {C['border_dark']};
    background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    color: {C['text_muted']} !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color: {C['text']} !important;
    border-bottom: 2px solid {C['text']} !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def sig_color(score, strong_buy=False):
    if strong_buy: return C["sbuy"]
    if score is None: return C["text_muted"]
    if score < BUY_THRESHOLD:  return C["buy"]
    if score > SELL_THRESHOLD: return C["sell"]
    return C["hold"]

def sig_bg(score, strong_buy=False):
    if strong_buy: return C["sbuy_bg"]
    if score is None: return C["surface2"]
    if score < BUY_THRESHOLD:  return C["buy_bg"]
    if score > SELL_THRESHOLD: return C["sell_bg"]
    return C["hold_bg"]

def sig_border(score, strong_buy=False):
    if strong_buy: return "#7AB8DC"
    if score is None: return C["border"]
    if score < BUY_THRESHOLD:  return C["buy_border"]
    if score > SELL_THRESHOLD: return C["sell_border"]
    return C["hold_border"]

def sig_label(score, strong_buy=False):
    if strong_buy: return "STRONG BUY"
    if score is None: return "N/A"
    if score < BUY_THRESHOLD:  return "BUY"
    if score > SELL_THRESHOLD: return "SELL"
    return "HOLD"

def sig_arrow(score, strong_buy=False):
    if strong_buy: return "▲▲"
    if score is None: return "—"
    if score < BUY_THRESHOLD:  return "▲"
    if score > SELL_THRESHOLD: return "▼"
    return "●"


@st.cache_data(ttl=REFRESH_SEC)
def load_scores():
    try:
        r = requests.get(GITHUB_RAW_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        # Return mock data for development/demo
        return _mock_scores()


def _mock_scores():
    """Demo data when GitHub URL is not configured."""
    import random
    random.seed(42)
    assets = {
        "Nifty":      {"price": 24180.0, "high_52w": 26277.0, "low_52w": 21964.0, "pe": 22.4, "rsi": 48.2},
        "Infosys":    {"price": 1842.0,  "high_52w": 2067.0,  "low_52w": 1358.0,  "pe": 27.1, "rsi": 42.7},
        "Reliance":   {"price": 2910.0,  "high_52w": 3217.0,  "low_52w": 2220.0,  "pe": 24.8, "rsi": 55.3},
        "ICICI Bank": {"price": 1290.0,  "high_52w": 1338.0,  "low_52w": 970.0,   "pe": 18.6, "rsi": 67.1},
    }
    scores_data = {}
    raw_scores  = [0.28, 0.41, 0.58, 0.72]
    for (name, meta), score in zip(assets.items(), raw_scores):
        sbuy = score < 0.30 and meta["rsi"] < 35
        scores_data[name] = {
            **meta,
            "master_score": score,
            "price_score":  round(score * 0.9 + random.uniform(-0.05, 0.05), 3),
            "pe_score":     round(score * 1.1 + random.uniform(-0.05, 0.05), 3),
            "vix_score":    0.38,
            "fx_score":     0.44,
            "signal":       sig_label(score, sbuy),
            "strong_buy":   sbuy,
        }
    scores_data["macro"] = {
        "vix":       14.8,
        "usdinr":    83.6,
        "vix_score": 0.38,
        "fx_score":  0.44,
    }
    return {
        "meta": {"updated_at": datetime.now().strftime("%d %b %Y %H:%M:%S IST"), "cycle": 47},
        **scores_data,
    }


# ── Chart factory ──────────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color=C["text"], size=11),
    margin=dict(t=30, b=30, l=10, r=10),
)


def chart_master_bars(scores):
    assets = list(scores.keys())
    vals   = [float(scores[a].get("master_score") or 0) for a in assets]
    colors = [sig_color(v, scores[a].get("strong_buy")) for a, v in zip(assets, vals)]
    borders= [sig_border(v, scores[a].get("strong_buy")) for a, v in zip(assets, vals)]

    fig = go.Figure()
    # Zone fills
    fig.add_hrect(y0=0,              y1=BUY_THRESHOLD,
                  fillcolor=C["buy_bg"], opacity=0.6, line_width=0)
    fig.add_hrect(y0=SELL_THRESHOLD, y1=1.1,
                  fillcolor=C["sell_bg"], opacity=0.6, line_width=0)

    fig.add_trace(go.Bar(
        x=assets, y=vals,
        marker_color=colors,
        marker_line_color=borders,
        marker_line_width=1,
        text=[f"{v:.3f}" for v in vals],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono, monospace", size=12, color=C["text"]),
        width=0.5,
        hovertemplate="<b>%{x}</b><br>Master Score: %{y:.3f}<extra></extra>",
    ))
    fig.add_hline(y=BUY_THRESHOLD,  line_dash="dot", line_color=C["buy"],
                  line_width=1.2,
                  annotation_text="BUY  ▼",
                  annotation_font=dict(color=C["buy"], size=10, family="IBM Plex Mono, monospace"),
                  annotation_position="top right")
    fig.add_hline(y=SELL_THRESHOLD, line_dash="dot", line_color=C["sell"],
                  line_width=1.2,
                  annotation_text="SELL  ▲",
                  annotation_font=dict(color=C["sell"], size=10, family="IBM Plex Mono, monospace"),
                  annotation_position="top right")

    fig.update_layout(
        **CHART_LAYOUT,
        yaxis=dict(range=[0, 1.15], gridcolor=C["grid"], tickformat=".2f",
                   title=dict(text="Score", font=dict(size=10, color=C["text_muted"])),
                   tickfont=dict(size=10, color=C["text_muted"])),
        xaxis=dict(tickfont=dict(size=12), linecolor=C["border_dark"]),
        height=300,
        showlegend=False,
    )
    return fig


def chart_sub_scores(scores):
    assets = list(scores.keys())
    comps  = [
        ("price_score", "Price"),
        ("pe_score",    "P/E Val."),
        ("vix_score",   "VIX"),
        ("fx_score",    "FX (₹)"),
    ]
    fig = go.Figure()
    for key, label in comps:
        vals = [round(float(scores[a].get(key) or 0), 3) for a in assets]
        fig.add_trace(go.Bar(
            name=label, x=assets, y=vals,
            marker_color=COMPONENT_COLORS[key],
            marker_line_width=0,
            text=[f"{v:.2f}" for v in vals],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono, monospace", size=10, color=C["text_muted"]),
            width=0.18,
        ))
    fig.add_hline(y=BUY_THRESHOLD,  line_dash="dot", line_color=C["buy"],
                  line_width=1, opacity=0.5)
    fig.add_hline(y=SELL_THRESHOLD, line_dash="dot", line_color=C["sell"],
                  line_width=1, opacity=0.5)

    fig.update_layout(
        **{**CHART_LAYOUT, "margin": dict(t=40, b=30, l=10, r=10)},
        barmode="group",
        yaxis=dict(range=[0, 1.25], gridcolor=C["grid"], tickformat=".2f",
                   tickfont=dict(size=10, color=C["text_muted"])),
        xaxis=dict(tickfont=dict(size=12), linecolor=C["border_dark"]),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, family="IBM Plex Mono, monospace"),
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        height=320,
    )
    return fig


def chart_52w_range(scores):
    assets = list(scores.keys())
    fig    = go.Figure()

    # Zone backgrounds (full width)
    fig.add_vrect(x0=0,              x1=BUY_THRESHOLD * 100,
                  fillcolor=C["buy_bg"], opacity=0.7, line_width=0)
    fig.add_vrect(x0=SELL_THRESHOLD * 100, x1=100,
                  fillcolor=C["sell_bg"], opacity=0.7, line_width=0)

    for asset in assets:
        s    = scores[asset]
        curr = float(s.get("price")   or 0)
        lo   = float(s.get("low_52w") or 0)
        hi   = float(s.get("high_52w")or 0)
        if hi <= lo or curr == 0:
            continue
        pct = max(0.0, min(100.0, (curr - lo) / (hi - lo) * 100))
        col = sig_color(pct / 100, s.get("strong_buy"))

        # Track
        fig.add_trace(go.Scatter(
            x=[0, 100], y=[asset, asset],
            mode="lines",
            line=dict(color=C["border"], width=8),
            showlegend=False, hoverinfo="skip",
        ))
        # Fill to current
        fig.add_trace(go.Scatter(
            x=[0, pct], y=[asset, asset],
            mode="lines",
            line=dict(color=col, width=8),
            showlegend=False, hoverinfo="skip",
        ))
        # Current price marker
        fig.add_trace(go.Scatter(
            x=[pct], y=[asset],
            mode="markers+text",
            marker=dict(size=13, color=C["surface"], symbol="circle",
                        line=dict(color=col, width=2.5)),
            text=[f" ₹{curr:,.0f}"],
            textposition="middle right",
            textfont=dict(color=col, size=11,
                          family="IBM Plex Mono, monospace"),
            showlegend=False,
            hovertemplate=(f"<b>{asset}</b><br>Price: ₹{curr:,.2f}<br>"
                           f"52W Low: ₹{lo:,.2f}<br>52W High: ₹{hi:,.2f}<br>"
                           f"Position: {pct:.1f}%<extra></extra>"),
        ))
        fig.add_annotation(x=0,   y=asset, text=f"₹{lo:,.0f}",
                           showarrow=False, xanchor="right", xshift=-8,
                           font=dict(color=C["buy"], size=9,
                                     family="IBM Plex Mono, monospace"))
        fig.add_annotation(x=100, y=asset, text=f"₹{hi:,.0f}",
                           showarrow=False, xanchor="left", xshift=8,
                           font=dict(color=C["sell"], size=9,
                                     family="IBM Plex Mono, monospace"))

    fig.add_vline(x=BUY_THRESHOLD  * 100, line_dash="dot",
                  line_color=C["buy"],  line_width=1.2)
    fig.add_vline(x=SELL_THRESHOLD * 100, line_dash="dot",
                  line_color=C["sell"], line_width=1.2)

    fig.update_layout(
        **{**CHART_LAYOUT, "margin": dict(t=10, b=40, l=80, r=80)},
        xaxis=dict(range=[-15, 145], ticksuffix="%",
                   gridcolor=C["grid"],
                   title=dict(text="Position in 52-Week Range",
                               font=dict(size=10, color=C["text_muted"])),
                   tickfont=dict(size=10, color=C["text_muted"]),
                   linecolor=C["border_dark"]),
        yaxis=dict(tickfont=dict(size=12), autorange="reversed",
                   linecolor=C["border_dark"]),
        height=280,
    )
    return fig


def chart_radar(scores):
    assets = list(scores.keys())
    cats   = ["Price", "P/E Val.", "VIX", "FX (₹)"]
    keys   = ["price_score","pe_score","vix_score","fx_score"]
    fig    = go.Figure()
    colors = list(ASSET_CHART_COLORS.values())

    for i, asset in enumerate(assets):
        s    = scores[asset]
        vals = [1 - float(s.get(k) or 0) for k in keys]  # invert: higher = better
        vals += [vals[0]]   # close radar

        fig.add_trace(go.Scatterpolar(
            r    = vals,
            theta= cats + [cats[0]],
            name = asset,
            line = dict(color=colors[i % len(colors)], width=1.8),
            fill = "toself",
            fillcolor=colors[i % len(colors)],
            opacity=0.15,
            hovertemplate=f"<b>{asset}</b><br>%{{theta}}: %{{r:.3f}}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono, monospace", color=C["text"], size=11),
        polar=dict(
            bgcolor=C["surface"],
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=C["grid"],
                            tickfont=dict(size=9, color=C["text_muted"]),
                            linecolor=C["border"]),
            angularaxis=dict(tickfont=dict(size=11,
                                           family="IBM Plex Mono, monospace",
                                           color=C["text"]),
                             linecolor=C["border"], gridcolor=C["border"]),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11, family="IBM Plex Mono, monospace"),
                    orientation="v", x=1.1),
        height=320,
        margin=dict(t=20, b=20, l=20, r=100),
    )
    return fig


def chart_macro_bars(macro):
    vix    = float(macro.get("vix")    or 0)
    usdinr = float(macro.get("usdinr") or 0)

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=["India VIX", "USD / INR (₹)"],
    )

    # VIX: lower = better (green)
    vix_color = C["buy"] if vix < 15 else (C["sell"] if vix > 25 else C["hold"])
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=vix,
        number=dict(font=dict(size=40, color=vix_color,
                              family="Playfair Display, serif"),
                    valueformat=".1f"),
        gauge=dict(
            axis=dict(range=[0, 40], tickcolor=C["text_muted"],
                      tickfont=dict(size=9, color=C["text_muted"]),
                      nticks=5),
            bar=dict(color=vix_color, thickness=0.25),
            bgcolor=C["grid"],
            borderwidth=0,
            steps=[
                dict(range=[0,  15], color=C["buy_bg"]),
                dict(range=[15, 25], color=C["hold_bg"]),
                dict(range=[25, 40], color=C["sell_bg"]),
            ],
            threshold=dict(line=dict(color=vix_color, width=2),
                           thickness=0.85, value=vix),
        ),
    ), row=1, col=1)

    # USDINR: lower = better for equities
    fx_color = C["buy"] if usdinr < 82 else (C["sell"] if usdinr > 86 else C["hold"])
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=usdinr,
        number=dict(font=dict(size=40, color=fx_color,
                              family="Playfair Display, serif"),
                    prefix="₹", valueformat=".2f"),
        gauge=dict(
            axis=dict(range=[72, 96], tickcolor=C["text_muted"],
                      tickfont=dict(size=9, color=C["text_muted"]),
                      nticks=5),
            bar=dict(color=fx_color, thickness=0.25),
            bgcolor=C["grid"],
            borderwidth=0,
            steps=[
                dict(range=[72, 82], color=C["buy_bg"]),
                dict(range=[82, 86], color=C["hold_bg"]),
                dict(range=[86, 96], color=C["sell_bg"]),
            ],
            threshold=dict(line=dict(color=fx_color, width=2),
                           thickness=0.85, value=usdinr),
        ),
    ), row=1, col=2)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono, monospace", color=C["text"]),
        height=240,
        margin=dict(t=50, b=10, l=20, r=20),
    )
    for ann in fig.layout.annotations:
        ann.font.family = "IBM Plex Sans, sans-serif"
        ann.font.size   = 12
        ann.font.color  = C["text_muted"]
    return fig


# ── Score bar HTML ─────────────────────────────────────────────────────────

def render_score_bars(s: dict) -> str:
    comps = [
        ("price_score", "Price"),
        ("pe_score",    "P/E Valuation"),
        ("vix_score",   "VIX"),
        ("fx_score",    "FX / Rupee"),
    ]
    html = ""
    for key, label in comps:
        val   = float(s.get(key) or 0)
        col   = sig_color(val)
        pct   = val * 100
        html += f"""
        <div class="score-bar-wrap">
            <div class="score-bar-header">
                <span>{label}</span>
                <span>{val:.3f}</span>
            </div>
            <div class="score-bar-track">
                <div class="score-bar-fill"
                     style="width:{pct:.1f}%; background:{col};"></div>
                <div class="score-bar-buy-line"></div>
                <div class="score-bar-sell-line"></div>
            </div>
        </div>"""
    return html


# ── Full scores table ──────────────────────────────────────────────────────

def make_scores_df(scores: dict) -> pd.DataFrame:
    rows = []
    for asset, s in scores.items():
        if asset == "macro": continue
        sbuy  = s.get("strong_buy", False)
        score = float(s.get("master_score") or 0)
        rsi   = s.get("rsi")
        rows.append({
            "Asset":         asset,
            "Price (₹)":     f"₹{float(s.get('price') or 0):,.2f}",
            "52W High":      f"₹{float(s.get('high_52w') or 0):,.2f}",
            "52W Low":       f"₹{float(s.get('low_52w') or 0):,.2f}",
            "P/E Ratio":     f"{s.get('pe'):.1f}" if s.get("pe") else "—",
            "RSI (14D)":     f"{rsi:.1f}" if rsi is not None else "—",
            "Price Score":   float(s.get("price_score") or 0),
            "P/E Score":     float(s.get("pe_score")    or 0),
            "VIX Score":     float(s.get("vix_score")   or 0),
            "FX Score":      float(s.get("fx_score")    or 0),
            "Master Score":  score,
            "Signal":        ("★ " if sbuy else "") + sig_label(score, sbuy),
        })
    return pd.DataFrame(rows)


# ── Main app ───────────────────────────────────────────────────────────────

def main():
    data = load_scores()

    if data is None:
        st.error("Could not load scoring data. Check GitHub URL in secrets.")
        st.stop()

    all_scores = {k: v for k, v in data.items() if k != "meta"}
    macro      = all_scores.pop("macro", {})
    scores     = all_scores
    meta       = data.get("meta", {})
    updated    = meta.get("updated_at", "—")
    cycle      = meta.get("cycle",      "—")
    now        = datetime.now().strftime("%d %b %Y  %H:%M:%S")

    # ── Masthead ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="masthead">
        <div>
            <div class="masthead-title">Quant India</div>
            <div class="masthead-sub">Multi-Asset Scoring &amp; Signal Dashboard</div>
        </div>
        <div class="masthead-right">
            <div><span class="live-dot"></span>Live &nbsp;·&nbsp; Cycle #{cycle}</div>
            <div>Data as of &nbsp;<strong>{updated}</strong></div>
            <div>Refreshed &nbsp;<strong>{now}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Macro summary strip ──────────────────────────────────────────────────
    vix    = float(macro.get("vix")    or 0)
    usdinr = float(macro.get("usdinr") or 0)
    vix_c  = C["buy"] if vix < 15 else (C["sell"] if vix > 25 else C["hold"])
    fx_c   = C["buy"] if usdinr < 82 else (C["sell"] if usdinr > 86 else C["hold"])
    vix_lbl= "LOW — CALM" if vix < 15 else ("HIGH — FEAR" if vix > 25 else "MODERATE")
    fx_lbl = "STRONG ₹" if usdinr < 82 else ("WEAK ₹" if usdinr > 86 else "STABLE ₹")

    mc1, mc2, mc3 = st.columns([1, 1, 2])
    with mc1:
        st.markdown(f"""
        <div class="macro-tile">
            <div style="flex:1">
                <div class="macro-label">India VIX</div>
                <div class="macro-value" style="color:{vix_c}">{vix:.2f}</div>
                <div class="macro-sub">{vix_lbl}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    with mc2:
        st.markdown(f"""
        <div class="macro-tile">
            <div style="flex:1">
                <div class="macro-label">USD / INR</div>
                <div class="macro-value" style="color:{fx_c}">₹{usdinr:.2f}</div>
                <div class="macro-sub">{fx_lbl}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    with mc3:
        buy_ct  = sum(1 for s in scores.values() if float(s.get("master_score") or 0) < BUY_THRESHOLD)
        hold_ct = sum(1 for s in scores.values()
                      if BUY_THRESHOLD <= float(s.get("master_score") or 0) <= SELL_THRESHOLD)
        sell_ct = sum(1 for s in scores.values() if float(s.get("master_score") or 0) > SELL_THRESHOLD)
        st.markdown(f"""
        <div class="macro-tile" style="gap:0">
            <div style="flex:1; text-align:center; padding:0 16px; border-right:1px solid {C['border']}">
                <div class="macro-label">Buy</div>
                <div class="macro-value" style="color:{C['buy']}">{buy_ct}</div>
                <div class="macro-sub">signals</div>
            </div>
            <div style="flex:1; text-align:center; padding:0 16px; border-right:1px solid {C['border']}">
                <div class="macro-label">Hold</div>
                <div class="macro-value" style="color:{C['hold']}">{hold_ct}</div>
                <div class="macro-sub">signals</div>
            </div>
            <div style="flex:1; text-align:center; padding:0 16px">
                <div class="macro-label">Sell</div>
                <div class="macro-value" style="color:{C['sell']}">{sell_ct}</div>
                <div class="macro-sub">signals</div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Signal cards ────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Current Signals</div>',
                unsafe_allow_html=True)

    cols = st.columns(len(scores))
    for col, (asset, s) in zip(cols, scores.items()):
        score  = float(s.get("master_score") or 0)
        sbuy   = s.get("strong_buy", False)
        color  = sig_color(score, sbuy)
        bg     = sig_bg(score, sbuy)
        bdr    = sig_border(score, sbuy)
        price  = float(s.get("price") or 0)
        rsi    = s.get("rsi")
        pe     = s.get("pe")
        signal = sig_label(score, sbuy)
        arrow  = sig_arrow(score, sbuy)
        rsi_c  = C["buy"] if rsi and rsi < 35 else (C["sell"] if rsi and rsi > 65 else C["text_muted"])
        rsi_s  = f"{rsi:.1f}" if rsi else "—"
        pe_s   = f"{pe:.1f}x" if pe else "—"

        with col:
            st.markdown(f"""
            <div class="sig-card" style="border-left:3px solid {color}; border-color:{bdr};
                         border-left-color:{color}; background:{bg}">
                <div class="card-ticker">{asset}</div>
                <div class="card-price">₹{price:,.2f}</div>
                <div class="card-score-row">
                    <div>
                        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                                    color:{C['text_muted']};margin-bottom:3px">MASTER SCORE</div>
                        <div class="card-score-val" style="color:{color}">{score:.3f}</div>
                    </div>
                    <div class="card-signal-pill"
                         style="background:{color}15; color:{color}; border:1px solid {color}40">
                        {arrow} {signal}
                    </div>
                </div>
                <div class="card-meta">
                    <span>RSI&nbsp;<span style="color:{rsi_c};font-weight:500">{rsi_s}</span></span>
                    <span>P/E&nbsp;{pe_s}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── Tabs ────────────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs([
        "SCORES & SIGNALS",
        "SCORE BREAKDOWN",
        "PRICE RANGE",
        "MACRO",
    ])

    with t1:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="section-label">Master Score by Asset</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(chart_master_bars(scores), use_container_width=True,
                            config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="section-label">Score Components — Radar</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(chart_radar(scores), use_container_width=True,
                            config={"displayModeBar": False})

        # Score bars for each asset
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Component Scores per Asset</div>',
                    unsafe_allow_html=True)
        bar_cols = st.columns(len(scores))
        for col, (asset, s) in zip(bar_cols, scores.items()):
            with col:
                score = float(s.get("master_score") or 0)
                col_  = sig_color(score, s.get("strong_buy"))
                st.markdown(f"""
                <div style="background:{C['surface']};border:1px solid {C['border']};
                             border-radius:3px;padding:16px 18px;margin-bottom:8px">
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                                letter-spacing:0.18em;color:{C['text_muted']};
                                margin-bottom:12px;text-transform:uppercase">{asset}</div>
                    {render_score_bars(s)}
                </div>""", unsafe_allow_html=True)

    with t2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Sub-Score Comparison — All Assets</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(chart_sub_scores(scores), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown(f"""
        <div style="background:{C['surface2']};border:1px solid {C['border']};
                     border-radius:3px;padding:12px 18px;
                     font-family:'IBM Plex Mono',monospace;font-size:11px;
                     color:{C['text_muted']};line-height:1.8">
            Score interpretation: &nbsp;
            <span style="color:{C['buy']}">● 0.00–0.35 = Bullish zone (BUY)</span> &nbsp;|&nbsp;
            <span style="color:{C['hold']}">● 0.35–0.65 = Neutral (HOLD)</span> &nbsp;|&nbsp;
            <span style="color:{C['sell']}">● 0.65–1.00 = Bearish zone (SELL)</span><br>
            Weights: Price 30% · P/E 30% · VIX 20% · FX 20%
        </div>""", unsafe_allow_html=True)

    with t3:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">52-Week Price Range Position</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(chart_52w_range(scores), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown(f"""
        <div style="background:{C['surface2']};border:1px solid {C['border']};
                     border-radius:3px;padding:12px 18px;
                     font-family:'IBM Plex Mono',monospace;font-size:11px;
                     color:{C['text_muted']};line-height:1.8">
            ◇ Diamond = current price &nbsp;|&nbsp;
            <span style="color:{C['buy']}">Green zone = near 52W low (BUY territory)</span> &nbsp;|&nbsp;
            <span style="color:{C['sell']}">Red zone = near 52W high (SELL territory)</span>
        </div>""", unsafe_allow_html=True)

    with t4:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Macro Indicators</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(chart_macro_bars(macro), use_container_width=True,
                        config={"displayModeBar": False})
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""
            <div style="background:{C['surface']};border:1px solid {C['border']};
                         border-radius:3px;padding:16px 20px">
                <div class="section-label" style="margin-bottom:10px">VIX Interpretation</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                             color:{C['text_muted']};line-height:2">
                    <span style="color:{C['buy']}">● Below 15</span> — Low fear, bullish environment<br>
                    <span style="color:{C['hold']}">● 15–25</span> — Moderate volatility, neutral<br>
                    <span style="color:{C['sell']}">● Above 25</span> — High fear, elevated risk
                </div>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div style="background:{C['surface']};border:1px solid {C['border']};
                         border-radius:3px;padding:16px 20px">
                <div class="section-label" style="margin-bottom:10px">USD/INR Interpretation</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                             color:{C['text_muted']};line-height:2">
                    <span style="color:{C['buy']}">● Below ₹82</span> — Strong rupee, bullish for FIIs<br>
                    <span style="color:{C['hold']}">● ₹82–86</span> — Stable, neutral impact<br>
                    <span style="color:{C['sell']}">● Above ₹86</span> — Weak rupee, bearish pressure
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── Full data table ──────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Full Scores Table</div>',
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
            "Price Score":  st.column_config.ProgressColumn(
                "Price Score",  min_value=0, max_value=1, format="%.3f"
            ),
            "P/E Score":    st.column_config.ProgressColumn(
                "P/E Score",    min_value=0, max_value=1, format="%.3f"
            ),
        },
    )

    dl1, dl2 = st.columns([1, 4])
    with dl1:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇  Download CSV",
            data=csv,
            file_name=f"quant_india_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-top:40px;padding-top:16px;border-top:1px solid {C['border']};
                 display:flex;justify-content:space-between;align-items:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:{C['text_muted']}">
            <strong style="color:{C['text']}">QUANT INDIA</strong>
            &nbsp;·&nbsp; Automated scoring system
            &nbsp;·&nbsp; Data: NSE / BSE via Yahoo Finance
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:{C['text_muted']}">
            Not investment advice &nbsp;·&nbsp;
            Auto-refreshes every {REFRESH_SEC}s
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh
    time.sleep(REFRESH_SEC)
    st.rerun()


if __name__ == "__main__":
    main()