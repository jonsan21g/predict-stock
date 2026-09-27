"""
features.py - Feature Engineering Pipeline for the Wave Rider Engine.
Transforms raw OHLCV price bars, volume series, smart-money disclosures,
and sentiment into high-signal quantitative feature matrices.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes technical momentum, volatility, and volume indicators on daily OHLCV bars.
    Returns an enriched DataFrame without forward lookahead bias.
    """
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # 1. Moving Averages
    df["EMA5"] = close.ewm(span=5, adjust=False).mean()
    df["EMA10"] = close.ewm(span=10, adjust=False).mean()
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["SMA50"] = close.rolling(window=50).mean()
    df["SMA200"] = close.rolling(window=200).mean()

    # Spreads (% distance from price to moving average)
    df["ema5_spread"] = (close - df["EMA5"]) / df["EMA5"]
    df["ema20_spread"] = (close - df["EMA20"]) / df["EMA20"]
    df["ema50_spread"] = (close - df["SMA50"]) / df["SMA50"]

    # Moving Average Alignment (1 if 5 EMA > 20 EMA > 50 SMA)
    df["ema_alignment"] = (
        (df["EMA5"] > df["EMA20"]) & (df["EMA20"] > df["SMA50"])
    ).astype(int)

    # 2. Relative Volume (RVOL) over 20-day baseline
    df["vol_sma20"] = volume.rolling(window=20).mean()
    df["rvol_20d"] = np.where(df["vol_sma20"] > 0, volume / df["vol_sma20"], 1.0)

    # 3. Volatility & Range (ATR)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(window=14).mean()
    df["atr_pct"] = np.where(close > 0, df["ATR14"] / close, 0.02)

    # 4. Closing Range Relative (CRR) - where in the day's candle did it close?
    day_range = high - low
    df["crr"] = np.where(day_range > 0, (close - low) / day_range, 0.5)

    # 5. Bollinger Band Squeeze & Expansion
    sma20 = close.rolling(window=20).mean()
    std20 = close.rolling(window=20).std()
    upper_bb = sma20 + (2.0 * std20)
    lower_bb = sma20 - (2.0 * std20)
    df["bb_width"] = np.where(sma20 > 0, (upper_bb - lower_bb) / sma20, 0.0)

    # Squeeze: bandwidth <= 20th percentile over past 60 sessions
    rolling_20th = df["bb_width"].rolling(window=60).quantile(0.20)
    df["bb_squeeze"] = (df["bb_width"] <= rolling_20th).astype(int)
    df["bb_breakout"] = (close > upper_bb).astype(int)

    # 6. Proximity to 20-Day and 50-Day Highs
    rolling_high_20 = high.rolling(window=20).max()
    rolling_high_50 = high.rolling(window=50).max()
    df["dist_to_20d_high"] = np.where(rolling_high_20 > 0, (close - rolling_high_20) / rolling_high_20, 0.0)
    df["dist_to_50d_high"] = np.where(rolling_high_50 > 0, (close - rolling_high_50) / rolling_high_50, 0.0)
    df["is_20d_high_breakout"] = (close >= rolling_high_20.shift(1)).astype(int)

    # 7. Momentum Return over last 3 days
    df["ret_3d"] = close.pct_change(3)

    return df


def create_wave_target(
    df: pd.DataFrame,
    target_pct: float = 0.035,
    stop_pct: float = 0.025,
    horizon_bars: int = 5
) -> pd.Series:
    """
    Creates the binary ground-truth target label:
    1 if within the next horizon_bars (5 days), Max(High) >= Entry * (1 + target_pct)
      AND Min(Low) > Entry * (1 - stop_pct).
    0 otherwise.
    Strictly forward-looking, computed only for model training/evaluation.
    """
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    n = len(df)
    labels = np.zeros(n, dtype=int)

    for i in range(n - horizon_bars):
        entry_price = close[i]
        forward_highs = high[i+1 : i + 1 + horizon_bars]
        forward_lows = low[i+1 : i + 1 + horizon_bars]

        max_high = np.max(forward_highs)
        min_low = np.min(forward_lows)

        hit_target = max_high >= (entry_price * (1.0 + target_pct))
        hit_stop = min_low <= (entry_price * (1.0 - stop_pct))

        # Win condition: reached target without violating stop loss
        if hit_target and not hit_stop:
            labels[i] = 1
        elif hit_target and hit_stop:
            # Check which occurred first
            target_idx = np.where(forward_highs >= entry_price * (1.0 + target_pct))[0][0]
            stop_idx = np.where(forward_lows <= entry_price * (1.0 - stop_pct))[0][0]
            labels[i] = 1 if target_idx < stop_idx else 0
        else:
            labels[i] = 0

    return pd.Series(labels, index=df.index, name="is_winning_wave")


def build_feature_matrix(
    df: pd.DataFrame,
    congress_signals: Optional[Dict[str, Any]] = None,
    insider_signals: Optional[Dict[str, Any]] = None,
    sentiment_signals: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Enriches daily OHLCV bars with technical indicators, smart money flags,
    and social sentiment into a complete feature matrix ready for ML inference or training.
    """
    enriched = compute_technical_indicators(df)

    has_pol_buy = 1 if congress_signals and congress_signals.get("has_recent_buy", False) else 0
    pol_buy_count = int(congress_signals.get("buy_count", 0)) if congress_signals else 0

    has_ins_buy = 1 if insider_signals and insider_signals.get("has_recent_buy", False) else 0
    ins_cluster = 1 if insider_signals and insider_signals.get("has_cluster_buy", False) else 0
    ins_score = float(insider_signals.get("insider_score", 0)) if insider_signals else 0.0

    sentiment_score = float(sentiment_signals.get("sentiment_score", 0.0)) if sentiment_signals else 0.0
    buzz_zscore = float(sentiment_signals.get("buzz_zscore", 0.0)) if sentiment_signals else 0.0

    enriched["has_politician_buy"] = has_pol_buy
    enriched["politician_buy_count"] = pol_buy_count
    enriched["has_insider_buy"] = has_ins_buy
    enriched["insider_cluster_buy"] = ins_cluster
    enriched["insider_score"] = ins_score
    enriched["social_sentiment"] = sentiment_score
    enriched["social_buzz_zscore"] = buzz_zscore

    enriched = enriched.dropna(subset=["SMA50", "ATR14", "bb_width"]).copy()

    return enriched


FEATURE_COLUMNS: List[str] = [
    "rvol_20d",
    "ema5_spread",
    "ema20_spread",
    "ema50_spread",
    "ema_alignment",
    "atr_pct",
    "crr",
    "bb_width",
    "bb_squeeze",
    "bb_breakout",
    "dist_to_20d_high",
    "dist_to_50d_high",
    "is_20d_high_breakout",
    "ret_3d",
    "has_politician_buy",
    "politician_buy_count",
    "has_insider_buy",
    "insider_cluster_buy",
    "insider_score",
    "social_sentiment",
    "social_buzz_zscore"
]
