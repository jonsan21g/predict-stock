"""
test_intraday_engine.py - Unit and Integration Tests for:
  - Market Hours Session Clock (FR-07-01)
  - Pre-Market Gap Isolation & Purity (FR-07-02)
  - Pre-Market Snapshot Persistence (FR-07-03)
  - Time-of-Day Cumulative Volume Pacing (FR-08-01)
  - Capitulation Reversal Snapback (ORCL Regression) (FR-08-02)
  - Trend Continuation Momentum ORB (FR-08-03)
  - Intraday REST API Route (FR-08-04)
"""

import pytest
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, time, timezone

from src.fetchers.market_hours import (
    get_current_market_session,
    MarketSession,
    is_regular_trading_hours,
    is_premarket_session,
    get_ny_now
)
from src.fetchers.premarket_snapshot import (
    save_premarket_snapshot,
    load_premarket_snapshot,
    has_premarket_snapshot
)
from src.analysis.volume_pacing import (
    get_expected_volume_fraction,
    calculate_pacing_rvol
)
from src.analysis.intraday_engine import (
    evaluate_intraday_stock,
    scan_intraday_watchlist
)
from src.dashboard.app import app


def test_market_session_clock():
    """FR-07-01: Validates that session clock correctly identifies all 4 sessions."""
    try:
        from zoneinfo import ZoneInfo
        ny_tz = ZoneInfo("America/New_York")
    except Exception:
        import pytz
        ny_tz = pytz.timezone("America/New_York")

    # Tuesday at 08:00 EST -> PRE_MARKET
    t_pre = datetime(2026, 9, 29, 8, 0, 0, tzinfo=ny_tz)
    assert get_current_market_session(t_pre) == MarketSession.PRE_MARKET
    assert is_premarket_session(t_pre) is True
    assert is_regular_trading_hours(t_pre) is False

    # Tuesday at 10:15 EST -> REGULAR_HOURS
    t_rth = datetime(2026, 9, 29, 10, 15, 0, tzinfo=ny_tz)
    assert get_current_market_session(t_rth) == MarketSession.REGULAR_HOURS
    assert is_regular_trading_hours(t_rth) is True

    # Tuesday at 17:30 EST -> AFTER_HOURS
    t_ah = datetime(2026, 9, 29, 17, 30, 0, tzinfo=ny_tz)
    assert get_current_market_session(t_ah) == MarketSession.AFTER_HOURS

    # Tuesday at 22:00 EST -> CLOSED
    t_closed = datetime(2026, 9, 29, 22, 0, 0, tzinfo=ny_tz)
    assert get_current_market_session(t_closed) == MarketSession.CLOSED

    # Saturday at 12:00 EST -> CLOSED
    t_sat = datetime(2026, 10, 3, 12, 0, 0, tzinfo=ny_tz)
    assert get_current_market_session(t_sat) == MarketSession.CLOSED


def test_premarket_quote_isolation():
    """FR-07-02: Verifies strict pre-market isolation flag and structure."""
    from src.fetchers.price_fetcher import get_premarket_quote

    quote = get_premarket_quote("ORCL", strict_premarket=True)
    assert isinstance(quote, dict)
    assert quote["ticker"] == "ORCL"
    assert "current_price" in quote
    assert "gap_pct" in quote
    assert quote.get("is_strict_premarket") is True


def test_premarket_snapshot_persistence(tmp_path):
    """FR-07-03: Tests freezing and loading an immutable pre-market snapshot."""
    test_date = "2026-09-29-test"
    dummy_records = [
        {"ticker": "ORCL", "gap_pct": 0.05, "is_ignition": False},
        {"ticker": "ARM", "gap_pct": 2.71, "is_ignition": True}
    ]

    saved_path = save_premarket_snapshot(dummy_records, date_str=test_date)
    assert os.path.exists(saved_path)
    assert has_premarket_snapshot(test_date) is True

    loaded = load_premarket_snapshot(test_date)
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0]["ticker"] == "ORCL"
    assert loaded[1]["ticker"] == "ARM"

    # Cleanup
    if os.path.exists(saved_path):
        os.remove(saved_path)


def test_volume_pacing_model():
    """FR-08-01: Verifies time-of-day U-curve expected volume and pacing calculation."""
    # 09:45 EST (15 mins into session) should expect ~9% of daily volume
    frac_945 = get_expected_volume_fraction(time(9, 45))
    assert 0.07 <= frac_945 <= 0.12

    # 12:00 EST (Midday) should expect ~40-45% of daily volume
    frac_noon = get_expected_volume_fraction(time(12, 0))
    assert 0.38 <= frac_noon <= 0.46

    # 10:00 EST: baseline average daily vol = 10,000,000.
    # Expected at 10:00 is 15% = 1,500,000.
    # If 2,250,000 has traded, pacing RVOL should be 1.50x
    pacing = calculate_pacing_rvol(cumulative_volume=2_250_000, vol_sma20=10_000_000, current_time=time(10, 0))
    assert 1.45 <= pacing <= 1.55


def test_intraday_orcl_snapback_regression():
    """
    FR-08-02: REGRESSION TEST FOR ORCL (Sept 28-29, 2026).
    Verifies that a stock with prior RSI <= 28, Lower BB touch,
    clearing 15m ORH on >= 1.30x volume pacing fires REVERSAL_SNAPBACK.
    """
    # Create 30 days of synthetic daily history ending in a capitulation drop
    dates = pd.date_range(end="2026-09-29", periods=35, freq="B")
    prices = np.linspace(165.0, 132.60, 35) # Downtrend from 165 to 132.60
    prices[-1] = 139.50 # Today bounce

    daily_df = pd.DataFrame({
        "Open": prices * 1.005,
        "High": prices * 1.02,
        "Low": prices * 0.98,
        "Close": prices,
        "Volume": [25_000_000] * 35
    }, index=dates)

    # Force prior day (Sept 28) to have extreme low RSI and Lower BB touch
    daily_df.iloc[-2, daily_df.columns.get_loc("Close")] = 132.60
    daily_df.iloc[-2, daily_df.columns.get_loc("Low")] = 131.50

    # 5m intraday bars for today (09:30 to 11:00 EST)
    intra_times = pd.date_range("2026-09-29 09:30", "2026-09-29 11:00", freq="5min", tz="America/New_York")
    intra_df = pd.DataFrame({
        "Open": np.linspace(132.80, 139.00, len(intra_times)),
        "High": np.linspace(133.50, 140.00, len(intra_times)),
        "Low": np.linspace(132.50, 138.80, len(intra_times)),
        "Close": np.linspace(133.00, 139.50, len(intra_times)),
        "Volume": [650_000] * len(intra_times) # Pacing > 1.30x (1.65x)
    }, index=intra_times)

    signal = evaluate_intraday_stock(
        ticker="ORCL",
        df_daily=daily_df,
        df_intraday=intra_df
    )

    assert signal["is_ignition"] is True
    assert signal["archetype"] == "REVERSAL_SNAPBACK"
    assert signal["composite_score"] >= 70
    assert signal["target_1"] > signal["entry_price"]
    assert signal["stop_loss"] < signal["entry_price"]
    assert "Capitulation Snapback" in signal["rationale"]


def test_intraday_momentum_orb():
    """
    FR-08-03: Verifies that an uptrend stock breaking out above 30m ORH
    on >= 1.40x volume pacing fires MOMENTUM_ORB.
    """
    dates = pd.date_range(end="2026-09-29", periods=35, freq="B")
    prices = np.linspace(120.0, 150.0, 35) # Uptrend from 120 to 150
    daily_df = pd.DataFrame({
        "Open": prices * 0.99,
        "High": prices * 1.01,
        "Low": prices * 0.98,
        "Close": prices,
        "Volume": [10_000_000] * 35
    }, index=dates)

    # 5m intraday bars: initial 30 mins at 150-152, then rips to 155 on heavy volume
    intra_times = pd.date_range("2026-09-29 09:30", "2026-09-29 11:30", freq="5min", tz="America/New_York")
    n = len(intra_times)
    c_prices = np.concatenate([np.linspace(150.0, 152.0, 6), np.linspace(152.5, 155.0, n - 6)])
    intra_df = pd.DataFrame({
        "Open": c_prices - 0.2,
        "High": c_prices + 0.3,
        "Low": c_prices - 0.3,
        "Close": c_prices,
        "Volume": [350_000] * n # High pacing
    }, index=intra_times)

    signal = evaluate_intraday_stock(
        ticker="NVDA",
        df_daily=daily_df,
        df_intraday=intra_df
    )

    assert signal["is_ignition"] is True
    assert signal["archetype"] == "MOMENTUM_ORB"
    assert signal["composite_score"] >= 70
    assert "Trend Breakout ORB" in signal["rationale"]


def test_dashboard_intraday_route():
    """FR-08-04: Verifies the Flask /api/radar?mode=intraday endpoint."""
    client = app.test_client()
    resp = client.get("/api/radar?mode=intraday&refresh=true")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "ticker" in first
        assert "is_ignition" in first
        assert "archetype" in first
        assert "pacing_rvol" in first
