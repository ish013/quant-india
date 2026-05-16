"""
data_fetcher.py
===============
Fetches all required market data via yfinance (free, no API key).

Data fetched
------------
  Per asset  : current price, 52-week high, 52-week low, P/E ratio
  Macro      : India VIX, USD/INR

P/E ratio note
--------------
  yfinance provides P/E for stocks but NOT for indices (Nifty).
  When paid API is connected later, replace _fetch_pe() only.
  Everything else stays unchanged.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

import config as cfg

log = logging.getLogger(__name__)

# ── Cache ──────────────────────────────────────────────────────────────────
_cache: dict = {}
_cache_time:  dict = {}
CACHE_TTL_SEC = 55   # slightly less than refresh interval


def _is_fresh(key: str) -> bool:
    if key not in _cache_time:
        return False
    return (datetime.now() - _cache_time[key]).seconds < CACHE_TTL_SEC


def _store(key: str, value):
    _cache[key]      = value
    _cache_time[key] = datetime.now()
    return value


# ── Single asset data ──────────────────────────────────────────────────────

def fetch_asset_data(symbol: str) -> dict:
    """
    Return dict with:
      price       float   current price
      high_52w    float   52-week high
      low_52w     float   52-week low
      pe          float   P/E ratio (None if unavailable)
      price_score float   normalized 0-1 position in 52w range
    """
    key = f"asset_{symbol}"
    if _is_fresh(key):
        return _cache[key]

    try:
        ticker = yf.Ticker(symbol)

        # --- Current price ---
        info  = ticker.fast_info
        price = getattr(info, "last_price", None) \
             or getattr(info, "previous_close", None)

        # --- 52-week high/low ---
        high_52w = getattr(info, "year_high", None)
        low_52w  = getattr(info, "year_low",  None)

        # Fallback: compute from 1yr history
        if not high_52w or not low_52w:
            hist     = ticker.history(period="1y")
            high_52w = float(hist["High"].max()) if not hist.empty else None
            low_52w  = float(hist["Low"].min())  if not hist.empty else None

        price    = float(price)    if price    else None
        high_52w = float(high_52w) if high_52w else None
        low_52w  = float(low_52w)  if low_52w  else None

        # --- P/E ratio ---
        pe = _fetch_pe(ticker, symbol)

        # --- Price Score ---
        price_score = None
        if price and high_52w and low_52w and (high_52w - low_52w) > 0:
            price_score = round(
                (price - low_52w) / (high_52w - low_52w), 4
            )

        result = {
            "symbol":      symbol,
            "price":       round(price,    2) if price    else None,
            "high_52w":    round(high_52w, 2) if high_52w else None,
            "low_52w":     round(low_52w,  2) if low_52w  else None,
            "pe":          round(pe,       2) if pe        else None,
            "price_score": price_score,
        }
        log.info("Fetched %s: price=%.2f 52H=%.2f 52L=%.2f PE=%s score=%s",
                 symbol,
                 price    or 0,
                 high_52w or 0,
                 low_52w  or 0,
                 f"{pe:.1f}" if pe else "N/A",
                 f"{price_score:.3f}" if price_score is not None else "N/A")

        return _store(key, result)

    except Exception as e:
        log.warning("fetch_asset_data(%s) failed: %s", symbol, e)
        return {
            "symbol": symbol, "price": None,
            "high_52w": None, "low_52w": None,
            "pe": None, "price_score": None,
        }


def _fetch_pe(ticker: yf.Ticker, symbol: str):
    """
    Try to get P/E ratio from yfinance.
    Returns None for indices (Nifty) — will be replaced by paid API later.
    """
    try:
        # yfinance info dict has trailingPE for stocks
        info = ticker.info
        pe   = info.get("trailingPE") or info.get("forwardPE")
        if pe and float(pe) > 0:
            return float(pe)
    except Exception:
        pass
    return None


# ── Macro data ─────────────────────────────────────────────────────────────

def fetch_vix() -> dict:
    """
    Return India VIX current value and normalized score.
    VIX score is INVERTED: high VIX = low score = buying opportunity.
    """
    key = "vix"
    if _is_fresh(key):
        return _cache[key]

    try:
        ticker = yf.Ticker(cfg.VIX_SYMBOL)
        info   = ticker.fast_info
        vix    = getattr(info, "last_price", None) \
              or getattr(info, "previous_close", None)
        vix    = float(vix)

        # Normalize and INVERT (high VIX = opportunity = low score)
        vix_min, vix_max = cfg.VIX_MIN, cfg.VIX_MAX
        vix_clamped      = max(vix_min, min(vix_max, vix))
        vix_score        = round(
            1 - (vix_clamped - vix_min) / (vix_max - vix_min), 4
        )

        result = {
            "vix":       round(vix, 2),
            "vix_score": vix_score,
        }
        log.info("VIX: %.2f → score=%.3f", vix, vix_score)
        return _store(key, result)

    except Exception as e:
        log.warning("fetch_vix() failed: %s", e)
        return {"vix": None, "vix_score": None}


def fetch_usdinr() -> dict:
    key = "usdinr"
    if _is_fresh(key):
        return _cache[key]

    try:
        rate = None

        # Try history-based fetch — more accurate than fast_info
        for symbol in ["INR=X", "USDINR=X"]:
            try:
                hist = yf.Ticker(symbol).history(period="5d", interval="1d")
                if not hist.empty:
                    val = float(hist["Close"].iloc[-1])
                    if not hist.empty:                    
                        val = float(hist["Close"].iloc[-1])
                        if val>0:
                            rate = val
                            break
            except Exception:
                continue

        # Try download() as second option
        if rate is None:
            try:
                import pandas as pd
                df = yf.download("INR=X", period="5d",
                                 interval="1d", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    val = float(df["Close"].iloc[-1])
                    if 75.0 <= val <= 90.0:
                        rate = val
                        log.info("USD/INR via download: %.4f", rate)
            except Exception:
                pass

        # Safe fallback
        if rate is None:
            rate = 84.50
            log.warning("USD/INR: all methods failed — using fallback %.2f", rate)

        mn, mx       = cfg.USDINR_MIN, cfg.USDINR_MAX
        rate_clamped = max(mn, min(mx, rate))
        fx_score     = round(1 - (rate_clamped - mn) / (mx - mn), 4)

        result = {"usdinr": round(rate, 4), "fx_score": fx_score}
        log.info("USD/INR: %.4f → score=%.3f", rate, fx_score)
        return _store(key, result)

    except Exception as e:
        log.warning("fetch_usdinr() failed: %s", e)
        return {"usdinr": None, "fx_score": None}


# ── Full snapshot ──────────────────────────────────────────────────────────

def fetch_all() -> dict:
    """
    Fetch everything in one call.
    Returns dict keyed by asset name + "macro".

    Structure:
    {
      "Nifty":    { price, high_52w, low_52w, pe, price_score },
      "Infosys":  { ... },
      "Reliance": { ... },
      "ICICI":    { ... },
      "macro":    { vix, vix_score, usdinr, fx_score },
    }
    """
    result = {}

    for name, symbol in cfg.ASSETS.items():
        result[name] = fetch_asset_data(symbol)

    macro         = fetch_vix()
    macro.update(fetch_usdinr())
    result["macro"] = macro

    return result