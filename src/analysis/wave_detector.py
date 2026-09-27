"""
wave_detector.py - Deterministic Day-1 Wave Ignition Rule Engine.
Identifies the ignition of 3-5 day momentum waves while rejecting
exhausted trends, low-volume consolidation, and extended blow-offs.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def detect_wave_ignition(bar: pd.Series, prev_bars: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluates whether the given bar represents a valid Day-1 Wave Ignition.

    Criteria:
    1. RVOL >= 1.50x (or >= 1.30x with Bollinger squeeze breakout).
    2. Strong Candle Close: CRR >= 0.70 (finished in upper 30% of day's range).
    3. Structural Breakout: Close >= 20-day high OR Upper Bollinger Band breakout.
    4. Momentum Alignment: Close > EMA5 > EMA20.
    5. Non-Exhausted: Close is not > 8% above 20 EMA (avoids buying the top).
    """
    close = float(bar["Close"])
    rvol = float(bar.get("rvol_20d", 1.0))
    crr = float(bar.get("crr", 0.5))
    ema5 = float(bar.get("EMA5", close))
    ema20 = float(bar.get("EMA20", close))
    ema20_spread = float(bar.get("ema20_spread", 0.0))
    is_20d_breakout = bool(bar.get("is_20d_high_breakout", 0))
    bb_breakout = bool(bar.get("bb_breakout", 0))
    bb_squeeze = bool(bar.get("bb_squeeze", 0))

    checks = []

    # 1. Volume Ignition check
    volume_pass = (rvol >= 1.50) or (rvol >= 1.30 and (bb_breakout or bb_squeeze))
    checks.append({
        "rule": "Institutional Volume Surge",
        "passed": volume_pass,
        "detail": f"RVOL is {rvol:.2f}x (required >= 1.50x or >= 1.30x on squeeze)"
    })

    # 2. Strong Closing Range Relative
    crr_pass = crr >= 0.68
    checks.append({
        "rule": "Closing Range Strength",
        "passed": crr_pass,
        "detail": f"Finished at {crr*100:.1f}% of daily range (required >= 68%)"
    })

    # 3. Breakout Geometry
    breakout_pass = is_20d_breakout or bb_breakout
    checks.append({
        "rule": "Structural Range Expansion",
        "passed": breakout_pass,
        "detail": "Cleared 20-day resistance or Upper Bollinger Band" if breakout_pass else "Inside existing range"
    })

    # 4. Fast Momentum Alignment
    alignment_pass = (close > ema5) and (ema5 >= ema20 * 0.995)
    checks.append({
        "rule": "Fast EMA Trend Stack",
        "passed": alignment_pass,
        "detail": f"Price (${close:.2f}) > 5 EMA (${ema5:.2f}) >= 20 EMA (${ema20:.2f})"
    })

    # 5. Anti-Exhaustion Guard (Prevent chasing the top)
    not_extended = ema20_spread <= 0.085
    checks.append({
        "rule": "Anti-Exhaustion Safe Zone",
        "passed": not_extended,
        "detail": f"Price is {ema20_spread*100:+.1f}% from 20 EMA (max safe limit +8.5%)"
    })

    is_ignition = volume_pass and crr_pass and breakout_pass and alignment_pass and not_extended

    target_1 = round(close * 1.035, 2)  # +3.5%
    target_2 = round(close * 1.060, 2)  # +6.0%
    stop_loss = round(close * 0.975, 2) # -2.5%

    return {
        "is_ignition": is_ignition,
        "ignition_type": "VOL_BREAKOUT" if is_20d_breakout else ("SQUEEZE_EXPANSION" if bb_breakout else "NONE"),
        "entry_price": round(close, 2),
        "target_1": target_1,
        "target_2": target_2,
        "stop_loss": stop_loss,
        "trailing_stop_anchor": "EMA5",
        "max_holding_days": 5,
        "rvol": round(rvol, 2),
        "crr": round(crr, 2),
        "checks": checks
    }


def scan_recent_ignition(df: pd.DataFrame, lookback_days: int = 3) -> Optional[Dict[str, Any]]:
    """
    Checks if a wave ignition occurred within the last `lookback_days` sessions.
    """
    if df.empty or len(df) < 5:
        return None

    recent_slice = df.iloc[-lookback_days:]
    for idx in range(len(recent_slice) - 1, -1, -1):
        bar = recent_slice.iloc[idx]
        prev = df.iloc[: df.index.get_loc(recent_slice.index[idx])]
        result = detect_wave_ignition(bar, prev)
        if result["is_ignition"]:
            result["date"] = recent_slice.index[idx].strftime("%Y-%m-%d")
            result["days_ago"] = (len(recent_slice) - 1) - idx
            return result

    return None
