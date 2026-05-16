"""
main_github.py — Pipeline that pushes scores.json to GitHub every cycle
========================================================================
Usage:
  python main_github.py           single run
  python main_github.py --loop    refresh every REFRESH_SEC seconds
"""

from datetime import timezone, timedelta
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

import config as cfg
from data_fetcher import fetch_all
from scorer        import score_all
from excel_writer  import write_dashboard

log = logging.getLogger(__name__)

# ── GitHub config (set these as environment variables) ─────────────────────
# Windows:  set GITHUB_TOKEN=your_token
#           set GITHUB_REPO=username/repo-name
#           set GITHUB_FILE=data/scores.json
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO",  "YOUR_USERNAME/YOUR_REPO")
GITHUB_FILE  = os.environ.get("GITHUB_FILE",  "data/scores.json")
GITHUB_API   = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"

_cycle = 0


# ── Logging setup ──────────────────────────────────────────────────────────
Path(cfg.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(cfg.LOG_FILE, encoding="utf-8"),
    ],
)


# ── GitHub push ────────────────────────────────────────────────────────────

def push_to_github(payload: dict) -> bool:
    """Push scores.json to GitHub repo. Returns True on success."""
    if not GITHUB_TOKEN:
        log.warning("GITHUB_TOKEN not set — skipping GitHub push")
        return False

    content = base64.b64encode(
        json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github.v3+json",
    }

    # Get current SHA (needed to update existing file)
    sha = None
    try:
        r = requests.get(GITHUB_API, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception as e:
        log.warning("Could not get file SHA: %s", e)

    # Push new content
    body = {
        "message": f"scores update — cycle #{payload['meta']['cycle']}",
        "content": content,
    }
    if sha:
        body["sha"] = sha

    try:
        r = requests.put(GITHUB_API, headers=headers,
                         json=body, timeout=15)
        if r.status_code in (200, 201):
            log.info("✅ GitHub push successful (cycle #%d)", payload["meta"]["cycle"])
            return True
        else:
            log.error("GitHub push failed: %s %s", r.status_code, r.text[:200])
            return False
    except Exception as e:
        log.error("GitHub push error: %s", e)
        return False


# ── Save local copy ────────────────────────────────────────────────────────

def save_local(payload: dict):
    """Save scores.json locally as backup."""
    path = Path("data/scores.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    log.info("Local scores.json saved → %s", path.resolve())


# ── RSI calculator ─────────────────────────────────────────────────────────

def compute_rsi(ticker_symbol, period=14):
    try:
        import yfinance as yf
        import pandas as pd
        df = yf.download(ticker_symbol, period="3mo", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < period + 1:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"].squeeze()
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss
        rsi   = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except Exception as e:
        log.warning("RSI failed for %s: %s", ticker_symbol, e)
        return None


# ── Main pipeline ──────────────────────────────────────────────────────────

def run_once():
    global _cycle
    _cycle += 1

    log.info("══ Pipeline starting (cycle #%d) ══", _cycle)

    # Step 1: Fetch
    log.info("Step 1/4 — Fetching market data...")
    all_data = fetch_all()
    macro    = all_data.pop("macro", {})
    asset_data = dict(all_data)

    vix    = macro.get("vix")
    usdinr = macro.get("usdinr")

    # Step 2: Score
    log.info("Step 2/4 — Computing scores...")
    combined          = dict(asset_data)
    combined["macro"] = macro
    scores = score_all(combined)

    # Inject RSI + Strong Buy
    for name, ticker in cfg.ASSETS.items():
        rsi = compute_rsi(ticker)
        if name in scores:
            scores[name]["rsi"] = rsi
            master = scores[name].get("master_score") or 1
            scores[name]["strong_buy"] = (
                rsi is not None and rsi < 30 and master < 0.35
            )

    # Step 3: Excel
    log.info("Step 3/4 — Writing Excel...")
    write_dashboard(scores)

    # Step 4: Build payload + push to GitHub
    log.info("Step 4/4 — Pushing to GitHub...")
    IST = timezone(timedelta(hours=5, minutes=30))

    payload = {
        "meta": {
          "updated_at": datetime.now(IST).strftime("%d %b %Y  %H:%M:%S IST"),
            "cycle":      _cycle,
        },
        "macro": macro,
    }
    payload.update(scores)

    save_local(payload)
    push_to_github(payload)

    # Print summary
    print("\n" + "═" * 66)
    print(f"  {'Asset':<14} {'Score':>6}  {'Signal':<14}  {'Price':>12}  {'RSI':>6}")
    print("─" * 66)
    for asset, s in scores.items():
        sig   = "★ STRONG BUY" if s.get("strong_buy") else s.get("signal", "N/A")
        score = float(s.get("master_score") or 0)
        price = float(s.get("price") or 0)
        rsi   = s.get("rsi")
        icon  = "🟢" if "BUY" in sig else ("🔴" if sig == "SELL" else "🟡")
        rsi_s = f"{rsi:.0f}" if rsi else "N/A"
        print(f"  {asset:<14} {score:>6.3f}  {icon} {sig:<12}  {price:>12,.2f}  {rsi_s:>6}")
    print("─" * 66)
    print(f"  VIX: {vix or 'N/A'}   USD/INR: {usdinr or 'N/A'}")
    print(f"  Cycle #{_cycle}   Updated: {payload['meta']['updated_at']}")
    print("═" * 66 + "\n")

    log.info("══ Pipeline complete (cycle #%d) ══\n", _cycle)
    return scores


def run_loop(interval=cfg.REFRESH_SEC):
    log.info("Loop mode. Refresh every %ds. Ctrl+C to stop.", interval)
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log.info("Stopped.")
            break
        except Exception as e:
            log.error("Error: %s", e, exc_info=True)
        log.info("Sleeping %ds…", interval)
        time.sleep(interval)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        run_loop()
    else:
        run_once()