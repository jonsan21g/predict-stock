"""
static_exporter.py - Cloud Snapshot & Static SPA Compiler.
Compiles the Wave Rider dashboard and dynamic API payloads into a self-contained
static directory ('dist/') that can be hosted on GitHub Pages or local HTTP servers
with zero Python/Flask backend runtime requirements.
"""

import os
import sys
import json
import shutil
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.fetchers.price_fetcher import load_watchlist, get_daily_history, get_premarket_quote
from src.analysis.features import compute_technical_indicators
from src.analysis.wave_classifier import scan_and_rank_watchlist, score_single_stock
from src.analysis.wave_detector import detect_wave_ignition
from src.analysis.intraday_engine import scan_intraday_watchlist
from src.backtest.backtester import run_wave_backtest
from src.game.duel import get_live_duel_status

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES_DIR = os.path.join(BASE_DIR, "src", "dashboard", "templates")
STATIC_SRC_DIR = os.path.join(BASE_DIR, "src", "dashboard", "static")


def build_health_payload() -> Dict[str, Any]:
    return {
        "status": "UP",
        "service": "Wave Rider Momentum Engine",
        "mode": "STATIC_CLOUD_BUNDLE",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }


def build_game_payload() -> Dict[str, Any]:
    status = get_live_duel_status()
    status["bot_auto_active"] = True
    status["next_bot_run"] = "Automated Cloud Action (Next ~30m)"
    status["exported_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return status


def build_radar_payload(mode: str = "eod") -> List[Dict[str, Any]]:
    mode = mode.lower().strip()
    if mode == "intraday":
        return scan_intraday_watchlist()
    elif mode == "premarket":
        stocks = load_watchlist()
        results = []
        for s in stocks:
            sym = s["ticker"]
            q = get_premarket_quote(sym, strict_premarket=True)
            gap = q.get("gap_pct", 0.0)
            price = q.get("current_price", 0.0)
            vol = q.get("volume", 0)
            is_gap = gap >= 1.0

            if is_gap:
                prob = round(min(90.0, max(55.0, 55.0 + gap * 5.0)), 1)
                score = int(min(98, max(50, 60 + int(gap * 6))))
            else:
                prob = round(max(35.0, min(50.0, 48.0 + gap * 2.0)), 1)
                score = int(max(20, min(50, 45 + int(gap * 3))))

            results.append({
                "ticker": sym,
                "name": s.get("name", sym),
                "category": s.get("category", "Tech"),
                "current_price": price,
                "change_pct": gap,
                "is_ignition": is_gap,
                "ignition_type": "PRE_MKT_GAP" if is_gap else "FLAT",
                "wave_probability": prob,
                "composite_score": score,
                "volume": vol,
                "target_1": round(price * 1.035, 2),
                "target_2": round(price * 1.060, 2),
                "stop_loss": round(price * 0.975, 2),
                "smart_money": {}
            })
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        return results
    else:
        return scan_and_rank_watchlist()


def build_stock_dossier(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    data = score_single_stock(ticker)
    
    # 60-day price history for interactive chart
    df = get_daily_history(ticker, period="6mo")
    enriched = compute_technical_indicators(df)
    recent_bars = enriched.iloc[-60:].copy()

    history = []
    for dt, row in recent_bars.iterrows():
        history.append({
            "date": dt.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
            "ema5": round(float(row["EMA5"]), 2) if "EMA5" in row else None,
            "ema20": round(float(row["EMA20"]), 2) if "EMA20" in row else None
        })

    latest_bar = enriched.iloc[-1]
    ignition = detect_wave_ignition(latest_bar, enriched.iloc[:-1])
    data["checks"] = ignition.get("checks", [])
    data["history"] = history

    watchlist = load_watchlist()
    match = next((s for s in watchlist if s["ticker"] == ticker), None)
    if match:
        data["name"] = match.get("name", ticker)
        data["category"] = match.get("category", "Tech")
        data["role"] = match.get("role", "")

    data["technicals"] = {
        "rvol_20d": round(float(latest_bar.get("rvol_20d", 1.0)), 2),
        "crr": round(float(latest_bar.get("crr", 0.5)), 2),
        "bb_width": round(float(latest_bar.get("bb_width", 0.0)), 3) if "bb_width" in latest_bar else None,
        "ema5": round(float(latest_bar.get("EMA5", 0.0)), 2) if "EMA5" in latest_bar else None,
        "ema20": round(float(latest_bar.get("EMA20", 0.0)), 2) if "EMA20" in latest_bar else None,
        "volume": int(latest_bar.get("Volume", 0)),
        "vol_sma20": int(latest_bar.get("vol_sma20", 0)) if "vol_sma20" in latest_bar else None,
        "high": round(float(latest_bar.get("High", 0.0)), 2),
        "low": round(float(latest_bar.get("Low", 0.0)), 2),
        "open": round(float(latest_bar.get("Open", 0.0)), 2)
    }
    return data


def build_backtest_bundle(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    bundle = {"ticker": ticker}
    
    # Pre-compute all three required lookback periods (1y, 2y, 3y)
    for p in ["1y", "2y", "3y"]:
        try:
            df = get_daily_history(ticker, period=p)
            enriched = compute_technical_indicators(df)
            res = run_wave_backtest(enriched, ticker=ticker)
            bundle[p] = res
        except Exception as e:
            bundle[p] = {"error": str(e), "ticker": ticker, "period": p}
            
    # Default top-level fields to 2y for backward compatibility
    if "2y" in bundle and "strategy_return_pct" in bundle["2y"]:
        for k, v in bundle["2y"].items():
            if k not in bundle:
                bundle[k] = v
                
    return bundle


def export_cloud_bundle(
    output_dir: str = "dist",
    mode: str = "fast",
    max_tickers: Optional[int] = None
) -> Dict[str, Any]:
    """
    Exports the entire frontend application and static data payloads to output_dir.
    Modes:
      - 'fast': Exports HTML/CSS/JS, health, game, and all 3 radar lists (<20s).
      - 'full': Exports fast assets PLUS all 50 stock dossiers and backtests.
    """
    t_start = time.time()
    out_path = os.path.abspath(os.path.join(BASE_DIR, output_dir))
    static_dst = os.path.join(out_path, "static")
    api_dst = os.path.join(out_path, "api")
    stock_dst = os.path.join(api_dst, "stock")
    backtest_dst = os.path.join(api_dst, "backtest")

    os.makedirs(static_dst, exist_ok=True)
    os.makedirs(stock_dst, exist_ok=True)
    os.makedirs(backtest_dst, exist_ok=True)

    files_exported = 0

    # 1. Copy Frontend Assets (adjusting index.html to relative paths if needed)
    src_html = os.path.join(TEMPLATES_DIR, "index.html")
    dst_html = os.path.join(out_path, "index.html")
    if os.path.exists(src_html):
        with open(src_html, "r", encoding="utf-8") as f:
            html_content = f.read()
        # Ensure relative asset paths for GitHub Pages subpath compatibility
        html_content = html_content.replace('href="/static/style.css', 'href="./static/style.css')
        html_content = html_content.replace('src="/static/app.js', 'src="./static/app.js')
        with open(dst_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        files_exported += 1

    src_css = os.path.join(STATIC_SRC_DIR, "style.css")
    dst_css = os.path.join(static_dst, "style.css")
    if os.path.exists(src_css):
        shutil.copy2(src_css, dst_css)
        files_exported += 1

    src_js = os.path.join(STATIC_SRC_DIR, "app.js")
    dst_js = os.path.join(static_dst, "app.js")
    if os.path.exists(src_js):
        shutil.copy2(src_js, dst_js)
        files_exported += 1

    # 2. Export Core System APIs
    health_data = build_health_payload()
    with open(os.path.join(api_dst, "health.json"), "w", encoding="utf-8") as f:
        json.dump(health_data, f, indent=2)
    files_exported += 1

    game_data = build_game_payload()
    with open(os.path.join(api_dst, "game.json"), "w", encoding="utf-8") as f:
        json.dump(game_data, f, indent=2)
    files_exported += 1

    # 3. Export Radar Modes
    for m in ["eod", "premarket", "intraday"]:
        target_radar_file = os.path.join(api_dst, f"radar_{m}.json")
        # In fast mode, reuse existing radar_eod if present to keep run under 20s
        if mode == "fast" and m == "eod" and os.path.exists(target_radar_file):
            continue
        try:
            radar_data = build_radar_payload(mode=m)
            with open(target_radar_file, "w", encoding="utf-8") as f:
                json.dump(radar_data, f, indent=2)
            files_exported += 1
        except Exception as e:
            print(f"[WARN] Failed exporting radar_{m}.json: {e}")

    # 4. Export Stock Dossiers and Backtest Bundles
    watchlist = load_watchlist()
    tickers = [s["ticker"] for s in watchlist]
    if max_tickers is not None:
        tickers = tickers[:max_tickers]

    # In fast mode, if stock/ or backtest/ are empty, export top 5 so tabs never break
    should_export_stocks = (mode == "full")
    if not should_export_stocks:
        existing_stocks = [f for f in os.listdir(stock_dst) if f.endswith(".json")]
        if len(existing_stocks) < 5:
            tickers_to_export = tickers[:5]
            should_export_stocks = True
        else:
            tickers_to_export = []
    else:
        tickers_to_export = tickers

    if should_export_stocks and tickers_to_export:
        print(f"[STATIC EXPORTER] Compiling {len(tickers_to_export)} stock dossiers and backtest bundles...")
        for sym in tickers_to_export:
            try:
                # Stock dossier
                stock_file = os.path.join(stock_dst, f"{sym}.json")
                if mode == "full" or not os.path.exists(stock_file):
                    sd = build_stock_dossier(sym)
                    with open(stock_file, "w", encoding="utf-8") as f:
                        json.dump(sd, f, indent=2)
                    files_exported += 1

                # Backtest bundle
                bt_file = os.path.join(backtest_dst, f"{sym}.json")
                if mode == "full" or not os.path.exists(bt_file):
                    bt = build_backtest_bundle(sym)
                    with open(bt_file, "w", encoding="utf-8") as f:
                        json.dump(bt, f, indent=2)
                    files_exported += 1
            except Exception as e:
                print(f"[WARN] Error compiling assets for {sym}: {e}")

    elapsed = round(time.time() - t_start, 2)
    summary = {
        "status": "SUCCESS",
        "mode": mode,
        "output_dir": out_path,
        "files_exported": files_exported,
        "elapsed_seconds": elapsed,
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    print(f"\n[STATIC EXPORTER] Export complete in {elapsed}s: {files_exported} files written to {out_path}")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Wave Rider Static Cloud Exporter")
    parser.add_argument("--dir", type=str, default="dist", help="Output directory name")
    parser.add_argument("--mode", type=str, default="fast", choices=["fast", "full"], help="Export mode: fast or full")
    parser.add_argument("--max-tickers", type=int, default=None, help="Optional ticker limit for testing")
    args = parser.parse_args()

    export_cloud_bundle(output_dir=args.dir, mode=args.mode, max_tickers=args.max_tickers)

