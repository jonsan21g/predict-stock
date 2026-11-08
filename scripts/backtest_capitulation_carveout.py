"""
backtest_capitulation_carveout.py - Quantitative Backtest of Capitulation Reversal Carve-Outs.
Evaluates whether buying severe washouts during Macro Downtrends (QQQ < 20-day EMA)
generates positive alpha across the 50-stock universe, comparing Unconfirmed Knife Catches
versus Next-Day Confirmation and testing multiple stop-loss models (-2.5%, -5.0%, LOD).
"""

import sys
import os
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import yfinance as yf

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.fetchers.price_fetcher import load_watchlist


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Computes technical indicators for daily bars."""
    df = df.copy()
    close = df["Close"]
    
    # 20-day EMA and SMA
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["SMA20"] = close.rolling(window=20).mean()
    
    # Bollinger Bands (20-day, 2 std)
    std20 = close.rolling(window=20).std()
    df["Lower_BB"] = df["SMA20"] - (2.0 * std20)
    df["Upper_BB"] = df["SMA20"] + (2.0 * std20)
    
    # 14-day RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    df["RSI14"] = df["RSI14"].fillna(50.0)
    
    # Daily return
    df["Return"] = close.pct_change()
    return df


def simulate_trade(
    df: pd.DataFrame,
    entry_idx: int,
    entry_price: float,
    stop_price: float,
    target_1_pct: float = 0.030,
    target_2_pct: float = 0.060,
    max_hold_days: int = 5
) -> Dict[str, Any]:
    """
    Simulates trade lifecycle bar-by-bar with conservative stop-before-target assumptions.
    Target 1 (+3%): Scales 50%, moves remaining stop to breakeven (entry_price).
    Target 2 (+6%): Closes remaining 50%.
    Stop Loss: Closes all remaining shares.
    Time Stop: Liquidates at Close on bar max_hold_days.
    """
    t1_price = entry_price * (1.0 + target_1_pct)
    t2_price = entry_price * (1.0 + target_2_pct)
    current_stop = stop_price
    
    hit_t1 = False
    remaining_fraction = 1.0
    realized_return = 0.0
    exit_date = df.index[entry_idx]
    exit_reason = "TIME_STOP"
    bars_held = 0
    
    total_len = len(df)
    for offset in range(1, max_hold_days + 1):
        idx = entry_idx + offset
        if idx >= total_len:
            break
            
        bar = df.iloc[idx]
        b_open = float(bar["Open"])
        b_high = float(bar["High"])
        b_low = float(bar["Low"])
        b_close = float(bar["Close"])
        bars_held = offset
        exit_date = df.index[idx]
        
        # 1. Conservative Stop Check First
        # If open gaps below stop, exit at open; otherwise exit at stop price
        if b_low <= current_stop:
            exit_p = min(b_open, current_stop)
            pnl_pct = (exit_p - entry_price) / entry_price
            realized_return += remaining_fraction * pnl_pct
            exit_reason = "BREAKEVEN_STOP" if hit_t1 else "STOP_LOSS"
            remaining_fraction = 0.0
            break
            
        # 2. Check Target 1
        if not hit_t1 and b_high >= t1_price:
            hit_t1 = True
            # Sell 50% at Target 1
            realized_return += 0.50 * target_1_pct
            remaining_fraction = 0.50
            # Elevate stop to at least breakeven (entry price)
            current_stop = max(current_stop, entry_price)
            
            # Check if Target 2 also reached on same bar
            if b_high >= t2_price:
                realized_return += 0.50 * target_2_pct
                remaining_fraction = 0.0
                exit_reason = "TARGET_2"
                break
                
        # 3. Check Target 2 on subsequent bars
        elif hit_t1 and b_high >= t2_price:
            realized_return += remaining_fraction * target_2_pct
            remaining_fraction = 0.0
            exit_reason = "TARGET_2"
            break
            
    # 4. Time Stop at end of holding window
    if remaining_fraction > 0:
        final_close = float(df.iloc[min(entry_idx + bars_held, total_len - 1)]["Close"])
        pnl_pct = (final_close - entry_price) / entry_price
        realized_return += remaining_fraction * pnl_pct
        if hit_t1:
            exit_reason = "T1_PLUS_TIME_STOP"
        else:
            exit_reason = "TIME_STOP"
            
    return {
        "entry_date": df.index[entry_idx].strftime("%Y-%m-%d"),
        "exit_date": exit_date.strftime("%Y-%m-%d"),
        "entry_price": round(entry_price, 2),
        "return_pct": round(realized_return * 100.0, 2),
        "is_win": realized_return > 0,
        "hit_t1": hit_t1,
        "exit_reason": exit_reason,
        "bars_held": bars_held
    }


def run_full_capitulation_backtest():
    print("=" * 80)
    print(" QUANTITATIVE BACKTEST: CAPITULATION REVERSAL CARVE-OUT ENGINE")
    print(" Period: 3 Years (Daily Bars) | Universe: 50 US Tech/Semis Leaders + QQQ")
    print(" Macro Condition: QQQ < 20-day EMA (Normally 100% Cash Frozen)")
    print("=" * 80)
    
    # 1. Load Watchlist
    watchlist = load_watchlist()
    tickers = [s["ticker"] for s in watchlist]
    print(f"Loaded {len(tickers)} tickers from watchlist. Downloading 3y historical data...")
    
    # 2. Batch Download Data
    all_tickers = list(set(tickers + ["QQQ"]))
    data = yf.download(all_tickers, period="3y", interval="1d", group_by="ticker", progress=False)
    
    # Extract QQQ
    if "QQQ" not in data.columns.levels[0]:
        print("[ERROR] Failed to download QQQ data.")
        return
        
    qqq_df = compute_indicators(data["QQQ"].dropna())
    qqq_dates = qqq_df.index
    
    # Extract Universe Stock Data
    stocks_data: Dict[str, pd.DataFrame] = {}
    for sym in tickers:
        try:
            if sym in data.columns.levels[0]:
                sdf = data[sym].dropna()
                if len(sdf) >= 60:
                    sdf = compute_indicators(sdf)
                    # Align with QQQ
                    sdf = sdf.reindex(qqq_dates).dropna()
                    if len(sdf) >= 60:
                        stocks_data[sym] = sdf
        except Exception:
            pass
            
    print(f"Successfully processed and aligned {len(stocks_data)} valid universe stocks.")
    
    # 3. Define the Test Matrix
    # Washout triggers:
    #   W1: Drop <= -6.0%
    #   W2: Drop <= -8.0%
    #   W3: Reversal Snapback (RSI <= 30 and (Low <= Lower_BB or Close/EMA20 - 1 <= -0.065))
    # Entry Modes:
    #   E1: Unconfirmed Knife Catch (Buy at Close of Washout Day T)
    #   E2: Next-Day Green Confirmation (Day T+1 Close > Open and Close > Day T Close, Buy at Close T+1)
    #   E3: Next-Day High Breach (Day T+1 High > Day T High, Buy at Day T High)
    # Stops:
    #   S1: -2.5% Hard Stop
    #   S2: -5.0% Wide Stop
    #   S3: Invalidation Stop (Washout Day Low - 0.5%)
    
    scenarios = [
        # --- Drop <= -6% ---
        {"name": "Drop <= -6% | Unconfirmed Knife Catch | Stop -2.5%", "washout": "DROP_6", "entry": "KNIFE_CLOSE", "stop": "STOP_2.5"},
        {"name": "Drop <= -6% | Unconfirmed Knife Catch | Stop -5.0%", "washout": "DROP_6", "entry": "KNIFE_CLOSE", "stop": "STOP_5.0"},
        {"name": "Drop <= -6% | Unconfirmed Knife Catch | Stop at LOD",  "washout": "DROP_6", "entry": "KNIFE_CLOSE", "stop": "STOP_LOD"},
        {"name": "Drop <= -6% | Next-Day Green Confirm   | Stop -2.5%", "washout": "DROP_6", "entry": "CONFIRM_GREEN", "stop": "STOP_2.5"},
        {"name": "Drop <= -6% | Next-Day Green Confirm   | Stop -5.0%", "washout": "DROP_6", "entry": "CONFIRM_GREEN", "stop": "STOP_5.0"},
        {"name": "Drop <= -6% | Next-Day Green Confirm   | Stop at LOD",  "washout": "DROP_6", "entry": "CONFIRM_GREEN", "stop": "STOP_LOD"},
        
        # --- Drop <= -8% (Extreme Capitulation) ---
        {"name": "Drop <= -8% | Unconfirmed Knife Catch | Stop -2.5%", "washout": "DROP_8", "entry": "KNIFE_CLOSE", "stop": "STOP_2.5"},
        {"name": "Drop <= -8% | Unconfirmed Knife Catch | Stop -5.0%", "washout": "DROP_8", "entry": "KNIFE_CLOSE", "stop": "STOP_5.0"},
        {"name": "Drop <= -8% | Unconfirmed Knife Catch | Stop at LOD",  "washout": "DROP_8", "entry": "KNIFE_CLOSE", "stop": "STOP_LOD"},
        {"name": "Drop <= -8% | Next-Day Green Confirm   | Stop -2.5%", "washout": "DROP_8", "entry": "CONFIRM_GREEN", "stop": "STOP_2.5"},
        {"name": "Drop <= -8% | Next-Day Green Confirm   | Stop -5.0%", "washout": "DROP_8", "entry": "CONFIRM_GREEN", "stop": "STOP_5.0"},
        {"name": "Drop <= -8% | Next-Day Green Confirm   | Stop at LOD",  "washout": "DROP_8", "entry": "CONFIRM_GREEN", "stop": "STOP_LOD"},

        # --- Reversal Snapback (RSI <= 30 & BB breach) ---
        {"name": "RSI<=30/BB  | Unconfirmed Knife Catch | Stop -2.5%", "washout": "SNAPBACK", "entry": "KNIFE_CLOSE", "stop": "STOP_2.5"},
        {"name": "RSI<=30/BB  | Unconfirmed Knife Catch | Stop -5.0%", "washout": "SNAPBACK", "entry": "KNIFE_CLOSE", "stop": "STOP_5.0"},
        {"name": "RSI<=30/BB  | Unconfirmed Knife Catch | Stop at LOD",  "washout": "SNAPBACK", "entry": "KNIFE_CLOSE", "stop": "STOP_LOD"},
        {"name": "RSI<=30/BB  | Next-Day Green Confirm   | Stop -2.5%", "washout": "SNAPBACK", "entry": "CONFIRM_GREEN", "stop": "STOP_2.5"},
        {"name": "RSI<=30/BB  | Next-Day Green Confirm   | Stop -5.0%", "washout": "SNAPBACK", "entry": "CONFIRM_GREEN", "stop": "STOP_5.0"},
        {"name": "RSI<=30/BB  | Next-Day Green Confirm   | Stop at LOD",  "washout": "SNAPBACK", "entry": "CONFIRM_GREEN", "stop": "STOP_LOD"},
    ]
    
    results_summary = []
    
    for sc in scenarios:
        w_type = sc["washout"]
        e_type = sc["entry"]
        s_type = sc["stop"]
        
        all_trades = []
        
        for sym, df in stocks_data.items():
            n_bars = len(df)
            # Skip first 30 bars for indicator stabilization
            i = 30
            while i < n_bars - 6:
                # 1. Macro Regime Check on Day T
                # QQQ Close < QQQ 20 EMA
                bar_date = df.index[i]
                if bar_date not in qqq_df.index:
                    i += 1
                    continue
                    
                qqq_close = float(qqq_df.loc[bar_date, "Close"])
                qqq_ema20 = float(qqq_df.loc[bar_date, "EMA20"])
                
                # Must be in Macro Downtrend
                if qqq_close >= qqq_ema20:
                    i += 1
                    continue
                    
                # 2. Check Washout Condition on Day T
                bar_t = df.iloc[i]
                ret_t = float(bar_t["Return"])
                rsi_t = float(bar_t["RSI14"])
                low_t = float(bar_t["Low"])
                lbb_t = float(bar_t["Lower_BB"])
                ema20_t = float(bar_t["EMA20"])
                close_t = float(bar_t["Close"])
                
                is_washout = False
                if w_type == "DROP_6" and ret_t <= -0.06:
                    is_washout = True
                elif w_type == "DROP_8" and ret_t <= -0.08:
                    is_washout = True
                elif w_type == "SNAPBACK":
                    spread = (close_t - ema20_t) / ema20_t
                    if rsi_t <= 30.0 and (low_t <= lbb_t or spread <= -0.065):
                        is_washout = True
                        
                if not is_washout:
                    i += 1
                    continue
                    
                # 3. Entry Logic
                entry_idx = -1
                entry_price = 0.0
                stop_price = 0.0
                
                if e_type == "KNIFE_CLOSE":
                    entry_idx = i
                    entry_price = close_t
                    
                    if s_type == "STOP_2.5":
                        stop_price = entry_price * 0.975
                    elif s_type == "STOP_5.0":
                        stop_price = entry_price * 0.950
                    elif s_type == "STOP_LOD":
                        # If entering at close, LOD is low_t. If close is near LOD, add minimum 1.5% buffer
                        lod_buffer = low_t * 0.995
                        stop_price = min(lod_buffer, entry_price * 0.985)
                        
                elif e_type == "CONFIRM_GREEN":
                    # Check Day T+1 for green confirmation
                    if i + 1 >= n_bars:
                        break
                    bar_t1 = df.iloc[i + 1]
                    c_t1 = float(bar_t1["Close"])
                    o_t1 = float(bar_t1["Open"])
                    
                    # Green confirmation: Close > Open and Close > Day T Close
                    if c_t1 > o_t1 and c_t1 > close_t:
                        entry_idx = i + 1
                        entry_price = c_t1
                        
                        if s_type == "STOP_2.5":
                            stop_price = entry_price * 0.975
                        elif s_type == "STOP_5.0":
                            stop_price = entry_price * 0.950
                        elif s_type == "STOP_LOD":
                            # Key technical level: Low of Day T (the washout anchor low)
                            stop_price = low_t * 0.995
                    else:
                        # Reversal NOT confirmed, knife avoided!
                        i += 1
                        continue
                        
                if entry_idx > 0 and entry_price > 0 and stop_price > 0:
                    trade_res = simulate_trade(
                        df=df,
                        entry_idx=entry_idx,
                        entry_price=entry_price,
                        stop_price=stop_price,
                        target_1_pct=0.030,
                        target_2_pct=0.060,
                        max_hold_days=5
                    )
                    trade_res["ticker"] = sym
                    all_trades.append(trade_res)
                    # Advance index past the trade holding period to prevent overlapping entries
                    i = entry_idx + max(1, trade_res["bars_held"])
                else:
                    i += 1
                    
        # Compute Statistics for this Scenario
        n_trades = len(all_trades)
        if n_trades == 0:
            results_summary.append({
                "Scenario": sc["name"],
                "Trades": 0,
                "Win Rate (%)": 0.0,
                "Profit Factor": 0.0,
                "Avg Return (%)": 0.0,
                "T1 Hit (%)": 0.0,
                "Gross Win": 0.0,
                "Gross Loss": 0.0
            })
            continue
            
        wins = [t for t in all_trades if t["is_win"]]
        losses = [t for t in all_trades if not t["is_win"]]
        t1_hits = [t for t in all_trades if t["hit_t1"]]
        
        win_rate = (len(wins) / n_trades) * 100.0
        t1_rate = (len(t1_hits) / n_trades) * 100.0
        avg_ret = sum(t["return_pct"] for t in all_trades) / n_trades
        
        gross_profit = sum(t["return_pct"] for t in wins)
        gross_loss = abs(sum(t["return_pct"] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.9
        
        results_summary.append({
            "Scenario": sc["name"],
            "Trades": n_trades,
            "Win Rate (%)": round(win_rate, 1),
            "Profit Factor": profit_factor,
            "Avg Return (%)": round(avg_ret, 2),
            "T1 Hit (%)": round(t1_rate, 1),
            "Gross Profit (%)": round(gross_profit, 1),
            "Gross Loss (%)": round(gross_loss, 1)
        })
        
    # Print Comparison Table
    res_df = pd.DataFrame(results_summary)
    print("\n" + "=" * 115)
    print("                      CAPITULATION CARVE-OUT BACKTEST RESULTS (3-YEAR HISTORICAL)")
    print("=" * 115)
    print(f"{'Scenario Name':<56} {'Trades':<7} {'Win%':<7} {'T1 Hit%':<9} {'Avg Ret%':<10} {'PF':<6}")
    print("-" * 115)
    for _, row in res_df.iterrows():
        print(f"{row['Scenario']:<56} {row['Trades']:<7} {row['Win Rate (%)']:<7.1f} {row['T1 Hit (%)']:<9.1f} {row['Avg Return (%)']:<+10.2f} {row['Profit Factor']:<6.2f}")
    print("=" * 115)
    
    # Save detailed CSV for reporting
    csv_out = os.path.join(os.path.dirname(__file__), "capitulation_backtest_results.csv")
    res_df.to_csv(csv_out, index=False)
    print(f"\nDetailed backtest results saved to {csv_out}")


if __name__ == "__main__":
    run_full_capitulation_backtest()
