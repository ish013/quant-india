"""
scorer.py
=========
Computes individual scores and master score for each asset.

Scoring logic (all scores 0-1, lower = cheaper/safer)
------------------------------------------------------
  Price Score  = (price - 52w_low)  / (52w_high - 52w_low)
  PE Score     = (pe - pe_min)      / (pe_max - pe_min)       ← N/A until paid API
  VIX Score    = 1 - (vix - vix_min) / (vix_max - vix_min)   ← inverted
  FX Score     = 1 - (usdinr - min) / (max - min)             ← inverted

Master Score = w1*Price + w2*PE + w3*VIX + w4*FX
  When PE unavailable, redistribute its weight to Price (30+30=60% price, 20% VIX, 20% FX)

Signal
------
  Score < 0.35  → BUY  (green)
  Score 0.35-0.65 → HOLD (yellow)
  Score > 0.65  → SELL (red)
"""

import logging

import config as cfg

log = logging.getLogger(__name__)


def compute_master_score(
    price_score: float,
    pe_score:    float,     # None if PE unavailable
    vix_score:   float,
    fx_score:    float,
) -> float:
    """
    Weighted master score.
    If PE unavailable, redistributes PE weight proportionally to other scores.
    Returns None if insufficient data.
    """
    scores  = {}
    weights = {}

    if price_score is not None:
        scores["price"]  = price_score
        weights["price"] = cfg.WEIGHTS["price"]

    if pe_score is not None:
        scores["pe"]     = pe_score
        weights["pe"]    = cfg.WEIGHTS["pe"]

    if vix_score is not None:
        scores["vix"]    = vix_score
        weights["vix"]   = cfg.WEIGHTS["vix"]

    if fx_score is not None:
        scores["fx"]     = fx_score
        weights["fx"]    = cfg.WEIGHTS["fx"]

    if not scores:
        return None

    # Normalize weights to sum to 1 (handles missing PE)
    total_weight = sum(weights.values())
    if total_weight == 0:
        return None

    master = sum(
        scores[k] * weights[k] / total_weight
        for k in scores
    )
    return round(master, 4)


def get_signal(score: float) -> str:
    """Convert master score to BUY / HOLD / SELL signal."""
    if score is None:
        return "N/A"
    if score < cfg.BUY_THRESHOLD:
        return "BUY"
    if score > cfg.SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


def score_all(data: dict) -> dict:
    """
    Compute scores for all assets using fetched data.

    Parameters
    ----------
    data : dict from data_fetcher.fetch_all()

    Returns
    -------
    dict keyed by asset name, each value:
    {
      price, high_52w, low_52w, pe,
      price_score, pe_score, vix_score, fx_score,
      master_score, signal,
      vix, usdinr,
    }
    """
    macro     = data.get("macro", {})
    vix_score = macro.get("vix_score")
    fx_score  = macro.get("fx_score")
    vix       = macro.get("vix")
    usdinr    = macro.get("usdinr")

    results = {}

    for name in cfg.ASSETS:
        asset = data.get(name, {})

        price_score = asset.get("price_score")
        pe          = asset.get("pe")

        # PE score — N/A until paid API provides historical PE range
        # When paid API ready: pe_score = (pe - pe_min) / (pe_max - pe_min)
        pe_score = None   # placeholder

        master = compute_master_score(
            price_score = price_score,
            pe_score    = pe_score,
            vix_score   = vix_score,
            fx_score    = fx_score,
        )
        signal = get_signal(master)

        results[name] = {
            # Raw data
            "price":       asset.get("price"),
            "high_52w":    asset.get("high_52w"),
            "low_52w":     asset.get("low_52w"),
            "pe":          pe,
            "vix":         vix,
            "usdinr":      usdinr,
            # Individual scores
            "price_score": price_score,
            "pe_score":    pe_score,      # None → shows N/A in Excel
            "vix_score":   vix_score,
            "fx_score":    fx_score,
            # Output
            "master_score": master,
            "signal":       signal,
        }

        log.info(
            "%s → price=%.2f | price_score=%s | vix_score=%s | "
            "fx_score=%s | master=%s | signal=%s",
            name,
            asset.get("price") or 0,
            f"{price_score:.3f}" if price_score is not None else "N/A",
            f"{vix_score:.3f}"   if vix_score   is not None else "N/A",
            f"{fx_score:.3f}"    if fx_score     is not None else "N/A",
            f"{master:.3f}"      if master        is not None else "N/A",
            signal,
        )

    return results