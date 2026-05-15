"""
main.py — Quant Scoring System Entry Point
==========================================
Runs the full pipeline:
  1. Fetch price, PE, VIX, USD/INR  (data_fetcher.py)
  2. Compute 52W range, PE score, VIX score, FX score  (scorer.py)
  3. Generate Master Score + BUY/HOLD/SELL signal
  4. Write results to Excel report  (excel_writer.py)
  5. Generate Plotly charts  (chart_plotter.py)
  6. Auto-open Excel on first run

Usage:
  python main.py                  single run
  python main.py --loop           refresh every REFRESH_SEC seconds
  python main.py --asset Nifty    single asset only
"""

import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import config as cfg
from data_fetcher import fetch_all
from scorer        import score_all
from excel_writer  import write_dashboard
from chart_plotter import build_dashboard

# ── Logging ────────────────────────────────────────────────────────────────
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
log = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────────────────────────
_cycle = 0
_prev_signals = {}


# ── Auto-open Excel ────────────────────────────────────────────────────────

def _open_excel():
    """Open the Excel file in the default application (first run only)."""
    path = str(Path(cfg.EXCEL_PATH).resolve())
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        log.info("Opened Excel → %s", path)
    except Exception as e:
        log.warning("Could not auto-open Excel: %s", e)


# ── Main pipeline ──────────────────────────────────────────────────────────

def run_once(asset_filter: str = None) -> dict:
    """Execute one full pipeline cycle. Returns scores dict."""
    global _cycle
    _cycle += 1

    log.info("══ Pipeline starting (cycle #%d) ══", _cycle)

    # ── Step 1: Fetch data ─────────────────────────────────────────────────
    log.info("Step 1/5 — Fetching market data...")
    all_data   = fetch_all()
    macro      = all_data.pop("macro", {})
    asset_data = all_data       # {Nifty:{...}, Infosys:{...}, ...}

    vix    = macro.get("vix")
    usdinr = macro.get("usdinr")
    log.info("  VIX=%.2f  USD/INR=%.2f", vix or 0, usdinr or 0)

    # ── Step 2+3: Score every asset ────────────────────────────────────────
    log.info("Step 2/5 — Computing scores...")
    combined_data          = dict(asset_data)
    combined_data["macro"] = macro
    scores = score_all(combined_data)   # score_all(data: dict) — no kwargs

    # ── Step 4: Excel report ───────────────────────────────────────────────
    log.info("Step 3/5 — Writing Excel report...")
    write_dashboard(scores)             # write_dashboard(scores) — no extra args

    # Auto-open Excel only on first cycle
    if _cycle == 1:
        _open_excel()

    # ── Step 5: Charts ─────────────────────────────────────────────────────
    log.info("Step 4/5 — Generating charts...")
    try:
        build_dashboard(
            scores     = scores,
            asset_data = asset_data,
            macro_data = {"vix": vix, "usdinr": usdinr},  # reuse already-fetched values
        )
    except Exception as e:
        log.warning("Chart generation failed: %s", e)

    # ── Print summary ──────────────────────────────────────────────────────
    log.info("Step 5/5 — Summary")
    print("\n" + "═" * 66)
    print(f"  {'Asset':<14} {'Score':>6}  {'Signal':<12}  {'Price':>12}  {'PE':>6}")
    print("─" * 66)
    for asset, s in scores.items():
        sig   = s.get("signal", "N/A")
        score = s.get("master_score", 0) or 0   # key is master_score not total_score
        price = s.get("price") or 0
        pe    = s.get("pe") or "N/A"
        icon  = "🟢" if sig == "BUY" else ("🔴" if sig == "SELL" else "🟡")
        print(f"  {asset:<14} {score:>6.3f}  {icon} {sig:<10}  {price:>12,.2f}  {str(pe):>6}")

    print("─" * 66)
    print(f"  India VIX  : {vix or 'N/A'}")
    print(f"  USD/INR    : {usdinr or 'N/A'}")
    print(f"  Excel      : {Path(cfg.EXCEL_PATH).resolve()}")
    print(f"  Charts     : {Path(cfg.OUTPUT_DIR).resolve()}")
    print(f"  Cycle      : #{_cycle}")
    print("═" * 66 + "\n")

    # Track signal changes
    for asset, s in scores.items():
        new_sig = s.get("signal", "HOLD")
        old_sig = _prev_signals.get(asset)
        if old_sig and old_sig != new_sig:
            log.warning("⚡ SIGNAL CHANGE  %s: %s → %s", asset, old_sig, new_sig)
        _prev_signals[asset] = new_sig

    log.info("══ Pipeline complete (cycle #%d) ══\n", _cycle)
    return scores


def run_loop(interval: int = cfg.REFRESH_SEC):   # config uses REFRESH_SEC
    """Continuous refresh loop — reruns pipeline every `interval` seconds."""
    log.info("Live mode started. Refresh every %ds. Ctrl+C to stop.", interval)
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log.info("Stopped by user.")
            break
        except Exception as e:
            log.error("Pipeline error: %s", e, exc_info=True)
        log.info("Sleeping %ds until next refresh…", interval)
        time.sleep(interval)


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asset_filter = None
    if "--asset" in sys.argv:
        idx = sys.argv.index("--asset")
        if idx + 1 < len(sys.argv):
            asset_filter = sys.argv[idx + 1]

    if "--loop" in sys.argv:
        run_loop()
    else:
        run_once(asset_filter=asset_filter)