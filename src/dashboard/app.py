"""
app.py - Local Interactive Web Dashboard for the Wave Rider Momentum Engine.
Runs locally at http://localhost:5050 with zero external cloud dependencies.
"""

import os
import sys
from typing import Dict, Any
from flask import Flask, render_template, jsonify, request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


from src.fetchers.price_fetcher import load_watchlist, get_daily_history, get_premarket_quote
from src.analysis.features import compute_technical_indicators
from src.analysis.wave_classifier import scan_and_rank_watchlist, score_single_stock
from src.analysis.wave_detector import detect_wave_ignition
from src.backtest.backtester import run_wave_backtest
from src.game.duel import (
    get_live_duel_status,
    execute_player_order,
    bot_evaluate_turn,
    initialize_game_state
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

# In-memory scan cache to make dashboard super snappy
RADAR_CACHE = {"eod": None, "premarket": None}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "UP", "service": "Wave Rider Momentum Engine"})


@app.route("/api/radar")
def api_radar():
    mode = request.args.get("mode", "eod").lower()
    refresh = request.args.get("refresh", "false").lower() == "true"

    if not refresh and RADAR_CACHE.get(mode):
        return jsonify(RADAR_CACHE[mode])

    if mode == "premarket":
        stocks = load_watchlist()
        results = []
        for s in stocks:
            sym = s["ticker"]
            q = get_premarket_quote(sym)
            gap = q.get("gap_pct", 0.0)
            price = q.get("current_price", 0.0)
            is_gap = gap >= 1.0

            results.append({
                "ticker": sym,
                "name": s.get("name", sym),
                "category": s.get("category", "Tech"),
                "current_price": price,
                "change_pct": gap,
                "is_ignition": is_gap,
                "ignition_type": "PRE_MKT_GAP" if is_gap else "FLAT",
                "wave_probability": round(min(95.0, max(40.0, 50.0 + gap * 8.0)), 1),
                "composite_score": int(min(100, max(20, 50 + int(gap * 10)))),
                "target_1": round(price * 1.035, 2),
                "target_2": round(price * 1.060, 2),
                "stop_loss": round(price * 0.975, 2),
                "smart_money": {}
            })
        results.sort(key=lambda x: x["composite_score"], reverse=True)
    else:
        results = scan_and_rank_watchlist()

    RADAR_CACHE[mode] = results
    return jsonify(results)


@app.route("/api/stock/<ticker>")
def api_stock(ticker):
    ticker = ticker.upper().strip()
    try:
        data = score_single_stock(ticker)
        # Add 60-day price history for interactive chart
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

        # Add ignition detailed checks
        latest_bar = enriched.iloc[-1]
        ignition = detect_wave_ignition(latest_bar, enriched.iloc[:-1])
        data["checks"] = ignition.get("checks", [])
        data["history"] = history
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/backtest")
def api_backtest():
    ticker = request.args.get("ticker", "NVDA").upper().strip()
    period = request.args.get("period", "2y")
    try:
        df = get_daily_history(ticker, period=period)
        enriched = compute_technical_indicators(df)
        res = run_wave_backtest(enriched, ticker=ticker)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/game")
def api_game():
    try:
        status = get_live_duel_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/game/order", methods=["POST"])
def api_game_order():
    try:
        payload = request.get_json(force=True)
        action = payload.get("action", "BUY")
        ticker = payload.get("ticker", "NVDA")
        shares = int(payload.get("shares", 0))
        res = execute_player_order(action=action, ticker=ticker, shares=shares)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/game/bot-turn", methods=["POST"])
def api_game_bot_turn():
    try:
        res = bot_evaluate_turn(force=True)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/game/reset", methods=["POST"])
def api_game_reset():
    try:
        res = initialize_game_state(force_reset=True)
        return jsonify({"status": "RESET", "state": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def run_dashboard(host="127.0.0.1", port=5050):
    print(f"\n[WAVE RIDER] Local Dashboard active at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)




if __name__ == "__main__":
    run_dashboard()
