"""
intraday_engine.py - Intraday Opening-Range Momentum & Capitulation Reversal Engine.
Implements:
  1. Archetype A: MOMENTUM_ORB (Trend Continuation Breakout, 30m window)
  2. Archetype B: REVERSAL_SNAPBACK (Capitulation Oversold Snapback, 15m window)
Combines Time-of-Day Volume Pacing, Opening Range High/Low boundaries, and VWAP.
"""

from typing import Dict, Any, List, Optional
import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, time, timezone

from src.fetchers.price_fetcher import get_daily_history, load_watchlist
from src.analysis.features import compute_technical_indicators
from src.analysis.volume_pacing import calculate_pacing_rvol
from src.fetchers.market_hours import get_ny_now, is_regular_trading_hours


def evaluate_intraday_stock(
    ticker: str,
    df_daily: Optional[pd.DataFrame] = None,
    df_intraday: Optional[pd.DataFrame] = None,
    smart_money: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates a single stock for Day-1 Intraday Ignitions:
      - REVERSAL_SNAPBACK: Capitulation bounce from extreme oversold conditions.
      - MOMENTUM_ORB: Trend continuation breakout above the 30-minute opening range high.
    """
    ticker = ticker.upper().strip()
    smart_money = smart_money or {}

    try:
        if df_daily is None or len(df_daily) < 25:
            df_daily = get_daily_history(ticker, period="3mo")

        ind_daily = compute_technical_indicators(df_daily)
        if len(ind_daily) < 2:
            return {"ticker": ticker, "is_ignition": False, "status": "INSUFFICIENT_HISTORY"}

        prior_day = ind_daily.iloc[-2]
        today_daily = ind_daily.iloc[-1]

        # Prior day indicators
        prior_close = float(prior_day["Close"])
        prior_high = float(prior_day["High"])
        prior_low = float(prior_day["Low"])
        prior_rsi = float(prior_day.get("RSI14", 50.0))
        prior_ema5 = float(prior_day.get("EMA5", prior_close))
        prior_ema20 = float(prior_day.get("EMA20", prior_close))
        prior_ema20_spread = float(prior_day.get("ema20_spread", 0.0))
        
        # Bollinger Bands for prior day
        sma20_prior = float(ind_daily["Close"].iloc[:-1].rolling(20).mean().iloc[-1])
        std20_prior = float(ind_daily["Close"].iloc[:-1].rolling(20).std().iloc[-1])
        prior_lower_bb = sma20_prior - (2.0 * std20_prior)

        # Baseline volume (20D average)
        vol_sma20 = float(ind_daily["Volume"].iloc[:-1].rolling(20).mean().iloc[-1])
        if vol_sma20 <= 0:
            vol_sma20 = float(today_daily["Volume"])

        # Fetch 5-minute intraday bars if not provided
        if df_intraday is None:
            t = yf.Ticker(ticker)
            df_intraday = t.history(period="1d", interval="5m", prepost=True)

        if df_intraday.empty:
            # Fallback to today daily
            cur_price = float(today_daily["Close"])
            today_open = float(today_daily["Open"])
            today_high = float(today_daily["High"])
            today_low = float(today_daily["Low"])
            cum_vol = int(today_daily["Volume"])
            vwap = cur_price
            orh_15 = max(today_open, today_high * 0.99)
            orl_15 = today_low
            orh_30 = orh_15
            orl_30 = orl_15
            pacing_rvol = 1.0
        else:
            try:
                ny_intra = df_intraday.tz_convert("America/New_York")
            except Exception:
                ny_intra = df_intraday
                
            rth_bars = ny_intra.between_time("09:30", "16:00")
            if rth_bars.empty:
                rth_bars = ny_intra

            cur_price = float(rth_bars["Close"].iloc[-1])
            today_open = float(rth_bars["Open"].iloc[0])
            today_high = float(rth_bars["High"].max())
            today_low = float(rth_bars["Low"].min())
            cum_vol = int(rth_bars["Volume"].sum())

            # VWAP
            typ_price = (rth_bars["High"] + rth_bars["Low"] + rth_bars["Close"]) / 3.0
            vwap = float((typ_price * rth_bars["Volume"]).sum() / max(1, cum_vol))

            # Opening ranges (15m = first 3 bars, 30m = first 6 bars)
            if len(rth_bars) >= 3:
                orh_15 = float(rth_bars.iloc[:3]["High"].max())
                orl_15 = float(rth_bars.iloc[:3]["Low"].min())
            else:
                orh_15 = today_high
                orl_15 = today_low

            if len(rth_bars) >= 6:
                orh_30 = float(rth_bars.iloc[:6]["High"].max())
                orl_30 = float(rth_bars.iloc[:6]["Low"].min())
            else:
                orh_30 = orh_15
                orl_30 = orl_15

            # Pacing RVOL calculation
            cur_time_est = rth_bars.index[-1].time() if hasattr(rth_bars.index[-1], "time") else get_ny_now().time()
            pacing_rvol = calculate_pacing_rvol(cum_vol, vol_sma20, cur_time_est)

        change_pct = ((cur_price - prior_close) / prior_close) * 100.0

        # =========================================================================
        # ARCHETYPE B: Capitulation Reversal Snapback (e.g. ORCL)
        # =========================================================================
        is_prior_oversold = (prior_rsi <= 28.0) and ((prior_low <= prior_lower_bb) or (prior_ema20_spread <= -0.065))
        vwap_confirmed = cur_price >= (vwap * 0.995)

        snapback_trigger = (
            is_prior_oversold
            and (cur_price > prior_high or cur_price > orh_15)
            and vwap_confirmed
            and cur_price > today_open
            and pacing_rvol >= 1.30
        )

        if snapback_trigger:
            target_1 = round(min(cur_price * 1.035, prior_ema20), 2)
            target_2 = round(prior_ema20, 2)
            stop_loss = round(max(orl_15, cur_price * 0.978), 2)
            score = int(min(100, 70 + int(pacing_rvol * 15)))

            rationale = (
                f"Capitulation Snapback: Prior RSI={prior_rsi:.1f}, "
                f"bounced off Lower BB (${prior_lower_bb:.2f}), cleared 15m ORH (${orh_15:.2f}) "
                f"on {pacing_rvol:.2f}x volume pace. Magnet target: 20 EMA (${prior_ema20:.2f})."
            )

            return {
                "ticker": ticker,
                "is_ignition": True,
                "archetype": "REVERSAL_SNAPBACK",
                "ignition_type": "REVERSAL_SNAPBACK",
                "entry_price": round(cur_price, 2),
                "current_price": round(cur_price, 2),
                "change_pct": round(change_pct, 2),
                "target_1": target_1,
                "target_2": target_2,
                "stop_loss": stop_loss,
                "pacing_rvol": pacing_rvol,
                "orh": round(orh_15, 2),
                "orl": round(orl_15, 2),
                "vwap": round(vwap, 2),
                "composite_score": score,
                "wave_probability": round(min(95.0, 65.0 + pacing_rvol * 12.0), 1),
                "rationale": rationale,
                "smart_money": smart_money
            }

        # =========================================================================
        # ARCHETYPE A: Trend Continuation Opening Range Breakout (MOMENTUM_ORB)
        # =========================================================================
        is_uptrend = (prior_close > prior_ema20) and (prior_ema5 >= prior_ema20 * 0.995)
        has_orb_breakout = (cur_price >= orh_30) or (cur_price >= orh_15 and rth_bars["High"].max() >= orh_30)
        
        momentum_orb_trigger = (
            is_uptrend
            and has_orb_breakout
            and vwap_confirmed
            and pacing_rvol >= 1.40
            and change_pct <= 6.5  # Anti-exhaustion limit
        )

        if momentum_orb_trigger:
            target_1 = round(cur_price * 1.035, 2)
            target_2 = round(cur_price * 1.060, 2)
            stop_loss = round(max(orl_30, cur_price * 0.978), 2)
            score = int(min(100, 72 + int(pacing_rvol * 12)))

            rationale = (
                f"Trend Breakout ORB: Uptrend intact (> 20 EMA), broke 30m ORH (${orh_30:.2f}) "
                f"on {pacing_rvol:.2f}x volume surge > VWAP (${vwap:.2f})."
            )

            return {
                "ticker": ticker,
                "is_ignition": True,
                "archetype": "MOMENTUM_ORB",
                "ignition_type": "MOMENTUM_ORB",
                "entry_price": round(cur_price, 2),
                "current_price": round(cur_price, 2),
                "change_pct": round(change_pct, 2),
                "target_1": target_1,
                "target_2": target_2,
                "stop_loss": stop_loss,
                "pacing_rvol": pacing_rvol,
                "orh": round(orh_30, 2),
                "orl": round(orl_30, 2),
                "vwap": round(vwap, 2),
                "composite_score": score,
                "wave_probability": round(min(95.0, 68.0 + pacing_rvol * 10.0), 1),
                "rationale": rationale,
                "smart_money": smart_money
            }

        # Non-ignition default
        classification = "WATCH_COILED_OVERSOLD" if is_prior_oversold else ("UPTREND_ACTIVE" if is_uptrend else "CONSOLIDATING")
        return {
            "ticker": ticker,
            "is_ignition": False,
            "archetype": classification,
            "ignition_type": "NONE",
            "entry_price": round(cur_price, 2),
            "current_price": round(cur_price, 2),
            "change_pct": round(change_pct, 2),
            "target_1": round(cur_price * 1.035, 2),
            "target_2": round(cur_price * 1.060, 2),
            "stop_loss": round(cur_price * 0.975, 2),
            "pacing_rvol": pacing_rvol,
            "orh": round(orh_30, 2),
            "orl": round(orl_30, 2),
            "vwap": round(vwap, 2),
            "composite_score": 45,
            "wave_probability": 42.0,
            "rationale": f"Holding inside range (Pacing {pacing_rvol:.2f}x).",
            "smart_money": smart_money
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "is_ignition": False,
            "archetype": "ERROR",
            "error": str(e)
        }


def scan_intraday_watchlist(watchlist: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Scans watchlist equities for active Intraday Ignitions (ORB & Capitulation Snapbacks).
    Returns ranked list sorted by ignition status and composite score.
    """
    stocks = watchlist or load_watchlist()
    results: List[Dict[str, Any]] = []

    for item in stocks:
        sym = item["ticker"]
        name = item.get("name", sym)
        category = item.get("category", "")
        
        signal = evaluate_intraday_stock(sym)
        if signal and not signal.get("error"):
            signal["name"] = name
            signal["category"] = category
            results.append(signal)

    # Sort: Ignitions first, then by composite score, then by change_pct
    results.sort(
        key=lambda x: (
            1 if x.get("is_ignition") else 0,
            x.get("composite_score", 0),
            x.get("change_pct", 0)
        ),
        reverse=True
    )
    return results
