"""
config.py — Central configuration for Quantitative Analyzer
Edit values here; no other file needs to change.
"""

# ── Assets to track ────────────────────────────────────────────────────────
ASSETS = {
    "Nifty":    "^NSEI",        # Nifty 50 Index
    "Infosys":  "INFY.NS",      # Infosys
    "Reliance": "RELIANCE.NS",  # Reliance Industries
    "ICICI":    "ICICIBANK.NS", # ICICI Bank
}

# ── Macro symbols ──────────────────────────────────────────────────────────
VIX_SYMBOL   = "^INDIAVIX"   # India VIX
USDINR_SYMBOL = "INR=X"   # USD/INR exchange rate


EXCEL_LIVE = "output/QuantAnalyzer_live.xlsx"

# ── Directories ────────────────────────────────────────────────────────────
DATA_DIR        = "data"
LOG_DIR         = "logs"
OUTPUT_DIR      = "output"
CHART_FILENAME  = "quant_dashboard.html"

# ── Score weights (must sum to 1.0) ───────────────────────────────────────
WEIGHTS = {
    "price": 0.30,   # 52-week position score
    "pe":    0.30,   # P/E score (N/A until paid API)
    "vix":   0.20,   # VIX fear score
    "fx":    0.20,   # USD/INR score
}

# ── Signal thresholds ──────────────────────────────────────────────────────
BUY_THRESHOLD  = 0.35   # Score < 0.35 → BUY
SELL_THRESHOLD = 0.65   # Score > 0.65 → SELL
                        # Between → HOLD

# ── Historical lookback for score normalization ────────────────────────────
LOOKBACK_YEARS = 5      # years of history for PE/VIX/FX min-max range

# ── VIX range (used when historical data insufficient) ────────────────────
VIX_MIN = 10.0
VIX_MAX = 35.0

# ── USD/INR range ──────────────────────────────────────────────────────────
USDINR_MIN = 83.0
USDINR_MAX = 100.0

# ── Excel output ───────────────────────────────────────────────────────────
EXCEL_PATH  = "output/QuantAnalyzer.xlsx"
SHEET_NAME  = "Dashboard"

# ── Refresh ────────────────────────────────────────────────────────────────
REFRESH_SEC = 60   # refresh every 60 seconds

# ── Logging ────────────────────────────────────────────────────────────────
LOG_FILE  = "logs/analyzer.log"
LOG_LEVEL = "INFO"


CHARTS_DIR    = OUTPUT_DIR        # charts saved inside output/ folder
EXCEL_REPORT  = EXCEL_PATH        # alias for main.py summary print
REFRESH_SECONDS = REFRESH_SEC     # alias for main.py run_loop()
