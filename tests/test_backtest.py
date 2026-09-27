import pytest
import pandas as pd
from src.fetchers.price_fetcher import get_daily_history
from src.analysis.features import compute_technical_indicators
from src.backtest.backtester import run_wave_backtest


def test_wave_backtest_execution():
    df = get_daily_history("NVDA", period="1y")
    enriched = compute_technical_indicators(df)
    results = run_wave_backtest(enriched, ticker="NVDA", initial_capital=10000.0)

    assert "total_trades" in results
    assert "win_rate_pct" in results
    assert "profit_factor" in results
    assert "equity_curve" in results
    assert "trades" in results
    assert isinstance(results["trades"], list)

    for t in results["trades"]:
        assert t["bars_held"] <= 5, f"Trade held {t['bars_held']} bars exceeding 5-day limit"
        assert "exit_reason" in t
        assert "pnl" in t
