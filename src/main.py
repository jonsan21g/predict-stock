"""
main.py - Dual-Cadence CLI for the Wave Rider Momentum Engine.
Usage:
    python -m src.main --mode eod                # Run evening End-of-Day scan
    python -m src.main --mode premarket          # Run morning Pre-Market gap check
    python -m src.main --backtest NVDA           # Run historical walkforward backtest
    python -m src.main --train                   # Retrain ML model on all 27 stocks
"""

import os
import sys
import argparse
from typing import List, Dict, Any
from datetime import datetime, timezone

from src.fetchers.price_fetcher import load_watchlist, get_premarket_quote, get_daily_history
from src.analysis.wave_classifier import scan_and_rank_watchlist, train_wave_model
from src.analysis.features import compute_technical_indicators
from src.backtest.backtester import run_wave_backtest
from src.game.duel import (
    get_live_duel_status,
    execute_player_order,
    bot_evaluate_turn,
    initialize_game_state
)
from src.game.duel import (
    get_live_duel_status,
    execute_player_order,
    bot_evaluate_turn,
    initialize_game_state
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_cli_table(results: List[Dict[str, Any]], mode: str = "eod", top_n: int = 10):
    """Prints a structured radar report to the terminal."""
    print("\n" + "=" * 94)
    print(f"  [WAVE RIDER] RADAR - {mode.upper()} SCAN ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")
    print(f"  Universe: 27 Top-Tier US Tech, Semiconductor & Memory Leaders")
    print("=" * 94)

    headers = f"{'#':<3} {'TICKER':<6} {'PRICE':<9} {'CHG/GAP':<9} {'IGNITION':<15} {'P(WAVE)':<9} {'SCORE':<7} {'TARGET 1':<10} {'STOP':<9} {'SMART MONEY'}"
    print(headers)
    print("-" * 94)

    for idx, item in enumerate(results[:top_n], start=1):
        ticker = item["ticker"]
        price = f"${item['current_price']:.2f}"
        chg = f"{item['change_pct']:+.2f}%"
        
        ignition_str = f"[*] {item['ignition_type']}" if item["is_ignition"] else "Consolidating"
        prob_str = f"{item['wave_probability']:.1f}%"
        score_str = f"{item['composite_score']}/100"
        t1_str = f"${item['target_1']:.2f}" if item.get("target_1") else "-"
        sl_str = f"${item['stop_loss']:.2f}" if item.get("stop_loss") else "-"

        sm = item.get("smart_money", {})
        badges = []
        if sm.get("politician_buy"):
            badges.append("[CONGRESS]")
        if sm.get("insider_cluster"):
            badges.append("[CLUSTER_BUY]")
        elif sm.get("insider_buy"):
            badges.append("[INSIDER]")
        if sm.get("sentiment_label") == "BULLISH":
            badges.append("[BULLISH]")

        badge_str = " ".join(badges) if badges else "-"

        row = f"{idx:<3} {ticker:<6} {price:<9} {chg:<9} {ignition_str:<15} {prob_str:<9} {score_str:<7} {t1_str:<10} {sl_str:<9} {badge_str}"
        print(row)


    print("-" * 92)
    print("  Exit Strategy: Target 1 (+3.5% scale 50%), Target 2 (+6.0% runner), Stop (-2.5% or 5 EMA), Time Stop (5 Days)")
    print("=" * 92 + "\n")


def run_eod_scan(top_n: int = 10):
    print("\nScanning 27 US Tech & Memory Leaders for Day-1 Wave Ignition...")
    results = scan_and_rank_watchlist()
    format_cli_table(results, mode="End-of-Day (EOD)", top_n=top_n)


def run_premarket_scan(top_n: int = 10):
    print("\nChecking Pre-Market Gap and Follow-Through Momentum...")
    stocks = load_watchlist()
    pm_results = []

    for s in stocks:
        sym = s["ticker"]
        quote = get_premarket_quote(sym)
        gap = quote.get("gap_pct", 0.0)
        price = quote.get("current_price", 0.0)

        # Flag gap-and-go candidate
        is_gap_and_go = gap >= 1.0

        pm_results.append({
            "ticker": sym,
            "current_price": price,
            "change_pct": gap,
            "is_ignition": is_gap_and_go,
            "ignition_type": "PRE_MKT_GAP" if is_gap_and_go else "FLAT",
            "wave_probability": min(95.0, max(40.0, 50.0 + gap * 8.0)),
            "composite_score": int(min(100, max(20, 50 + int(gap * 10)))),
            "target_1": round(price * 1.035, 2),
            "target_2": round(price * 1.060, 2),
            "stop_loss": round(price * 0.975, 2),
            "smart_money": {}
        })

    pm_results.sort(key=lambda x: x["change_pct"], reverse=True)
    format_cli_table(pm_results, mode="Pre-Market (PM)", top_n=top_n)


def run_single_backtest(ticker: str, period: str = "2y"):
    ticker = ticker.upper().strip()
    print(f"\nRunning 5-Day Wave Walkforward Backtest for {ticker} over {period}...")
    df = get_daily_history(ticker, period=period)
    enriched = compute_technical_indicators(df)
    res = run_wave_backtest(enriched, ticker=ticker)

    print("\n" + "=" * 60)
    print(f"  BACKTEST RESULTS: {ticker} (Strategy vs Buy & Hold)")
    print("=" * 60)
    print(f"  Initial Capital:        ${res['initial_capital']:,.2f}")
    print(f"  Ending Balance:         ${res['final_balance']:,.2f}")
    print(f"  Strategy Return:        {res['strategy_return_pct']:+.2f}%")
    print(f"  Buy & Hold Return:      {res['buy_and_hold_return_pct']:+.2f}%")
    print(f"  Total Trades:           {res['total_trades']}")
    print(f"  Win Rate:               {res['win_rate_pct']:.1f}% ({res['wins']}W / {res['losses']}L)")
    print(f"  Profit Factor:          {res['profit_factor']:.2f}")
    print(f"  Expectancy Per Trade:   ${res['expectancy_dollar']:+.2f}")
    print(f"  Max Drawdown:           {res['max_drawdown_pct']:.2f}%")
    print(f"  Avg Holding Period:     {res['avg_bars_held']} Days")
    print("-" * 60)

    if res["trades"]:
        print("\n  Recent Executed Trades:")
        for t in res["trades"][:5]:
            pnl_sign = "+" if t["pnl"] >= 0 else ""
            print(f"  • {t['entry_date']} -> {t['exit_date']} | Fill: ${t['entry_price']:.2f} Exit: ${t['exit_price']:.2f} | PnL: {pnl_sign}${t['pnl']:.2f} ({pnl_sign}{t['return_pct']}%) | [{t['exit_reason']}]")

    print("=" * 60 + "\n")


def print_duel_scoreboard():
    """Prints the live 5-Day Duel scoreboard and disclosures to terminal."""
    status = get_live_duel_status()
    print("\n" + "=" * 88)
    print("  [WAVE RIDER] 5-DAY LIVE PAPER TRADING DUEL: PLAYER VS. BOT")
    print(f"  Countdown: {status['countdown']}")
    print(f"  Leader Status: {status['lead_label']}")
    print("=" * 88)

    p = status["player"]
    b = status["bot"]

    print("\n  [SCOREBOARD]")
    p_sign = "+" if p["total_pnl"] >= 0 else ""
    b_sign = "+" if b["total_pnl"] >= 0 else ""
    print(f"  👤 PLAYER Net Equity:  ${p['net_equity']:>10,.2f} | P&L: {p_sign}${p['total_pnl']:>8.2f} ({p_sign}{p['total_pnl_pct']:>5.2f}%) | Cash: ${p['cash']:>9,.2f} | Stocks: ${p['stock_value']:>9,.2f}")
    print(f"  🤖 BOT Net Equity:     ${b['net_equity']:>10,.2f} | P&L: {b_sign}${b['total_pnl']:>8.2f} ({b_sign}{b['total_pnl_pct']:>5.2f}%) | Cash: ${b['cash']:>9,.2f} | Stocks: ${b['stock_value']:>9,.2f}")
    print("-" * 88)

    print("\n  [PLAYER OPEN POSITIONS]")
    if p["positions"]:
        for pos in p["positions"]:
            pnl_sign = "+" if pos["unrealized_pnl"] >= 0 else ""
            print(f"    • {pos['ticker']:<5} {pos['shares']:>4} shs @ ${pos['avg_price']:.2f} (Live: ${pos['current_price']:.2f}) | Val: ${pos['market_value']:,.2f} | PnL: {pnl_sign}${pos['unrealized_pnl']:.2f} ({pnl_sign}{pos['unrealized_pnl_pct']}%)")
    else:
        print("    (No open positions. 100% Cash)")

    print("\n  [BOT OPEN POSITIONS]")
    if b["positions"]:
        for pos in b["positions"]:
            pnl_sign = "+" if pos["unrealized_pnl"] >= 0 else ""
            print(f"    • {pos['ticker']:<5} {pos['shares']:>4} shs @ ${pos['avg_price']:.2f} (Live: ${pos['current_price']:.2f}) | Val: ${pos['market_value']:,.2f} | PnL: {pnl_sign}${pos['unrealized_pnl']:.2f} ({pnl_sign}{pos['unrealized_pnl_pct']}%)")
    else:
        print("    (No open positions. 100% Cash)")

    if b.get("decision_logs"):
        print("\n  [BOT TRANSPARENT RATIONALE & CATALYST FEED (Recent)]")
        for log in reversed(b["decision_logs"][-3:]):
            print(f"    • [{log['time']}] {log['action']} {log['shares']} {log['ticker']} @ ${log['price']:.2f} (Val: ${log['total_usd']:,.2f})")
            print(f"      Thesis: \"{log['rationale']}\"")

    print("=" * 88 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Wave Rider Momentum Engine CLI")
    parser.add_argument("--mode", choices=["eod", "premarket"], default="eod", help="Scanning mode (eod or premarket)")
    parser.add_argument("--top", type=int, default=10, help="Number of top candidates to display")
    parser.add_argument("--backtest", type=str, default="", help="Run backtest on a specific ticker (e.g. NVDA, MU)")
    parser.add_argument("--period", type=str, default="2y", help="Historical backtest period (e.g. 1y, 2y, 3y)")
    parser.add_argument("--train", action="store_true", help="Retrain ML model on all watchlist historical data")
    parser.add_argument("--duel", action="store_true", help="Display 5-Day Player vs. Bot Duel scoreboard & portfolio")
    parser.add_argument("--bot-turn", action="store_true", help="Trigger autonomous Bot evaluation & execution cycle")
    parser.add_argument("--reset-duel", action="store_true", help="Reset 5-Day Duel to starting $30,000 cash balance")
    parser.add_argument("--order", nargs=3, metavar=("ACTION", "TICKER", "SHARES"), help="Execute Player order (e.g. --order BUY NVDA 20)")

    args = parser.parse_args()

    if args.reset_duel:
        initialize_game_state(force_reset=True)
        print("\n[WAVE RIDER] 5-Day Duel successfully reset to initial $30,000.00 cash.")
        print_duel_scoreboard()
        return

    if args.order:
        action, ticker, shares_str = args.order
        try:
            shares = int(shares_str)
            res = execute_player_order(action=action, ticker=ticker, shares=shares)
            print(f"\n[WAVE RIDER] Order Filled: {res['action']} {res['shares']} {res['ticker']} @ ${res['price']:.2f} (Total: ${res['tx']['total_usd']:,.2f})")
            print_duel_scoreboard()
        except Exception as e:
            print(f"\n[ERROR] Order execution failed: {e}\n")
        return

    if args.bot_turn:
        print("\n[WAVE RIDER] Running Autonomous Bot Decision Engine...")
        res = bot_evaluate_turn(force=True)
        print(f"Bot evaluation completed at {res['time']}.")
        if res["actions_count"] > 0:
            for act in res["actions_taken"]:
                print(f"  • {act}")
        else:
            print("  • No allocation adjustments required at this time.")
        print_duel_scoreboard()
        return

    if args.duel:
        print_duel_scoreboard()
        return

    if args.train:
        print("\nTraining Calibrated Wave Classifier on Watchlist Equities...")
        res = train_wave_model()
        print(f"Model successfully saved to {res['model_file']} (Trained on {res['sample_count']} samples, Mean AUC: {res['mean_cv_auc']})\n")
        return

    if args.backtest:
        run_single_backtest(args.backtest, period=args.period)
        return

    if args.mode == "premarket":
        run_premarket_scan(top_n=args.top)
    else:
        run_eod_scan(top_n=args.top)


if __name__ == "__main__":
    main()

