"""
backtester.py - Historical Walkforward Simulation Engine for the Wave Rider Strategy.
Simulates bar-by-bar execution without lookahead bias, enforcing realistic 3-5 day
targets (+3.5% / +6.0%), a -2.5% stop loss, dynamic 5-EMA trailing, and a 5-day time stop.
"""

import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.analysis.features import compute_technical_indicators
from src.analysis.wave_detector import detect_wave_ignition


def run_wave_backtest(
    df: pd.DataFrame,
    ticker: str = "ASSET",
    initial_capital: float = 10000.0,
    risk_per_trade_pct: float = 1.5,
    target_1_pct: float = 0.035,
    target_2_pct: float = 0.060,
    stop_loss_pct: float = 0.025,
    max_hold_days: int = 5
) -> Dict[str, Any]:
    """
    Executes a walkforward backtest of the Wave Rider strategy on daily bars.
    """
    if "rvol_20d" not in df.columns or "EMA5" not in df.columns:
        df = compute_technical_indicators(df)

    if len(df) < 60:
        return {"error": "Insufficient bars for backtesting (requires >= 60 bars)"}

    warmup_bars = 50
    test_df = df.iloc[warmup_bars:].copy()

    balance = float(initial_capital)
    peak_balance = float(initial_capital)
    max_drawdown_pct = 0.0

    in_trade = False
    pos: Optional[Dict[str, Any]] = None
    trades: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []

    start_date = test_df.index[0].strftime("%Y-%m-%d")
    equity_curve.append({"date": start_date, "balance": round(balance, 2)})

    for i in range(len(test_df)):
        bar = test_df.iloc[i]
        date_str = test_df.index[i].strftime("%Y-%m-%d")
        bar_high = float(bar["High"])
        bar_low = float(bar["Low"])
        bar_close = float(bar["Close"])
        bar_ema5 = float(bar.get("EMA5", bar_close))

        # 1. Manage Open Position
        if in_trade and pos is not None:
            pos["bars_held"] += 1

            # Check Stop Loss
            if bar_low <= pos["stop_loss"]:
                exit_price = pos["stop_loss"]
                pnl = (exit_price - pos["entry_price"]) * pos["remaining_shares"]
                pos["realized_pnl"] += pnl
                balance += pnl

                is_win = pos["realized_pnl"] > 0
                trades.append({
                    "id": len(trades) + 1,
                    "ticker": ticker,
                    "entry_date": pos["entry_date"],
                    "exit_date": date_str,
                    "entry_price": round(pos["entry_price"], 2),
                    "exit_price": round(exit_price, 2),
                    "shares": pos["initial_shares"],
                    "pnl": round(pos["realized_pnl"], 2),
                    "return_pct": round((pos["realized_pnl"] / (pos["initial_shares"] * pos["entry_price"])) * 100, 2),
                    "bars_held": pos["bars_held"],
                    "result": "WIN" if is_win else "LOSS",
                    "exit_reason": "Trailing EMA Stop" if pos["hit_t1"] else "Initial Stop-Loss (-2.5%)"
                })
                in_trade = False
                pos = None

            # Check Target 1 (+3.5% scale out 50%)
            elif not pos["hit_t1"] and bar_high >= pos["target_1"]:
                pos["hit_t1"] = True
                scale_shares = pos["initial_shares"] // 2
                if scale_shares > 0:
                    scale_pnl = (pos["target_1"] - pos["entry_price"]) * scale_shares
                    pos["realized_pnl"] += scale_pnl
                    pos["remaining_shares"] -= scale_shares
                    balance += scale_pnl

                pos["stop_loss"] = max(pos["entry_price"] * 0.995, bar_ema5)

            # Check Target 2 (+6.0% runner liquidation)
            elif pos["hit_t1"] and bar_high >= pos["target_2"]:
                exit_price = pos["target_2"]
                runner_pnl = (exit_price - pos["entry_price"]) * pos["remaining_shares"]
                pos["realized_pnl"] += runner_pnl
                balance += runner_pnl

                trades.append({
                    "id": len(trades) + 1,
                    "ticker": ticker,
                    "entry_date": pos["entry_date"],
                    "exit_date": date_str,
                    "entry_price": round(pos["entry_price"], 2),
                    "exit_price": round(exit_price, 2),
                    "shares": pos["initial_shares"],
                    "pnl": round(pos["realized_pnl"], 2),
                    "return_pct": round((pos["realized_pnl"] / (pos["initial_shares"] * pos["entry_price"])) * 100, 2),
                    "bars_held": pos["bars_held"],
                    "result": "WIN",
                    "exit_reason": "Full Target 2 Reached (+6.0%)"
                })
                in_trade = False
                pos = None

            # Check 5-Day Time Stop
            elif pos is not None and pos["bars_held"] >= max_hold_days:
                exit_price = bar_close
                pnl = (exit_price - pos["entry_price"]) * pos["remaining_shares"]
                pos["realized_pnl"] += pnl
                balance += pnl

                is_win = pos["realized_pnl"] > 0
                trades.append({
                    "id": len(trades) + 1,
                    "ticker": ticker,
                    "entry_date": pos["entry_date"],
                    "exit_date": date_str,
                    "entry_price": round(pos["entry_price"], 2),
                    "exit_price": round(exit_price, 2),
                    "shares": pos["initial_shares"],
                    "pnl": round(pos["realized_pnl"], 2),
                    "return_pct": round((pos["realized_pnl"] / (pos["initial_shares"] * pos["entry_price"])) * 100, 2),
                    "bars_held": pos["bars_held"],
                    "result": "WIN" if is_win else "LOSS",
                    "exit_reason": f"{max_hold_days}-Day Time Stop (Capital Recycled)"
                })
                in_trade = False
                pos = None

            elif pos is not None and pos["hit_t1"]:
                pos["stop_loss"] = max(pos["stop_loss"], bar_ema5)

            if balance > peak_balance:
                peak_balance = balance
            dd = ((peak_balance - balance) / peak_balance) * 100.0
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd

            equity_curve.append({"date": date_str, "balance": round(balance, 2)})

        # 2. Look for Day-1 Wave Ignition
        elif not in_trade:
            prev_slice = test_df.iloc[:i]
            ignition = detect_wave_ignition(bar, prev_slice)

            if ignition["is_ignition"]:
                entry_price = bar_close
                target_1 = entry_price * (1.0 + target_1_pct)
                target_2 = entry_price * (1.0 + target_2_pct)
                stop_loss = entry_price * (1.0 - stop_loss_pct)

                risk_per_share = entry_price - stop_loss
                account_risk_dollars = balance * (risk_per_trade_pct / 100.0)
                shares = int(math.floor(account_risk_dollars / risk_per_share)) if risk_per_share > 0 else 0

                max_shares = int(balance // entry_price) if entry_price > 0 else 0
                shares = min(shares, max_shares)

                if shares >= 2:
                    in_trade = True
                    pos = {
                        "entry_date": date_str,
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "target_1": target_1,
                        "target_2": target_2,
                        "initial_shares": shares,
                        "remaining_shares": shares,
                        "realized_pnl": 0.0,
                        "hit_t1": False,
                        "bars_held": 0
                    }

    if in_trade and pos is not None:
        exit_price = float(test_df["Close"].iloc[-1])
        pnl = (exit_price - pos["entry_price"]) * pos["remaining_shares"]
        pos["realized_pnl"] += pnl
        balance += pnl
        is_win = pos["realized_pnl"] > 0
        trades.append({
            "id": len(trades) + 1,
            "ticker": ticker,
            "entry_date": pos["entry_date"],
            "exit_date": test_df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(pos["entry_price"], 2),
            "exit_price": round(exit_price, 2),
            "shares": pos["initial_shares"],
            "pnl": round(pos["realized_pnl"], 2),
            "return_pct": round((pos["realized_pnl"] / (pos["initial_shares"] * pos["entry_price"])) * 100, 2),
            "bars_held": pos["bars_held"],
            "result": "WIN" if is_win else "LOSS",
            "exit_reason": "End of Testing Period"
        })
        equity_curve.append({"date": test_df.index[-1].strftime("%Y-%m-%d"), "balance": round(balance, 2)})

    total_trades = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

    avg_win = (gross_profit / win_count) if win_count > 0 else 0.0
    avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0.0
    expectancy = ((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss)
    avg_bars_held = (sum(t["bars_held"] for t in trades) / total_trades) if total_trades > 0 else 0.0

    first_price = float(test_df["Close"].iloc[0])
    last_price = float(test_df["Close"].iloc[-1])
    buy_hold_ret = ((last_price - first_price) / first_price) * 100.0
    strategy_ret = ((balance - initial_capital) / initial_capital) * 100.0

    return {
        "ticker": ticker,
        "initial_capital": round(initial_capital, 2),
        "final_balance": round(balance, 2),
        "net_profit": round(balance - initial_capital, 2),
        "strategy_return_pct": round(strategy_ret, 2),
        "buy_and_hold_return_pct": round(buy_hold_ret, 2),
        "total_trades": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "win_rate_pct": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "expectancy_dollar": round(expectancy, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_bars_held": round(avg_bars_held, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "equity_curve": equity_curve,
        "trades": trades[::-1]
    }
