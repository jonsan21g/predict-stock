import os
import pytest
import pandas as pd
from src.fetchers.price_fetcher import load_watchlist, get_daily_history, get_premarket_quote


def test_watchlist_structure():
    stocks = load_watchlist()
    assert len(stocks) == 50, f"Expected 50 tickers, found {len(stocks)}"
    tickers = [s["ticker"] for s in stocks]
    for required in ["MU", "WDC", "STX", "SKHY", "SNDK", "NVDA", "DELL", "MSFT", "TSLA", "PLTR", "SNPS", "ORCL", "VRT"]:
        assert required in tickers, f"Missing {required} in watchlist"
        
    for item in stocks:
        assert "ticker" in item
        assert "name" in item
        assert "category" in item
        assert "exchange" in item


def test_daily_history_fetch():
    df = get_daily_history("NVDA", period="1mo")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) >= 15
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in df.columns
    assert isinstance(df.index, pd.DatetimeIndex)


def test_premarket_quote():
    quote = get_premarket_quote("AAPL")
    assert isinstance(quote, dict)
    assert quote["ticker"] == "AAPL"
    assert "current_price" in quote
    assert quote["current_price"] > 0
    assert "gap_pct" in quote
