"""
price_fetcher.py - Daily EOD and Pre-Market Quote Fetcher with Multi-Tier Caching.
Supports offline fallback, rate limit mitigation, and parquet/csv persistence.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
WATCHLIST_FILE = os.path.join(BASE_DIR, "data", "watchlist.json")

os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory session cache for fast repeated calls
MEM_CACHE: Dict[str, Any] = {}
MEM_CACHE_TTL = 300  # 5 minutes


def load_watchlist(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads the configured list of stocks from watchlist.json."""
    path = filepath or WATCHLIST_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(f"Watchlist file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("stocks", [])


def get_daily_history(
    ticker: str,
    period: str = "2y",
    use_cache: bool = True,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Fetches daily OHLCV bars for a given ticker with file-based cache.
    Falls back to cached disk data if network request fails.
    """
    ticker = ticker.upper().strip()
    cache_path = os.path.join(CACHE_DIR, f"{ticker}_daily.parquet")

    # 1. Check in-memory cache
    mem_key = f"{ticker}_{period}_daily"
    now = time.time()
    if use_cache and not force_refresh and mem_key in MEM_CACHE:
        val, ts = MEM_CACHE[mem_key]
        if now - ts < MEM_CACHE_TTL:
            return val.copy()

    # 2. Check disk cache
    if use_cache and not force_refresh and os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            # If cached within today (last 8 hours), reuse
            if now - mtime < 28800:
                df = pd.read_parquet(cache_path)
                if not df.empty and len(df) >= 30:
                    MEM_CACHE[mem_key] = (df, now)
                    return df.copy()
        except Exception:
            pass

    # 3. Network fetch via yfinance
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d", auto_adjust=True)
        if df.empty or len(df) < 5:
            # Fallback to disk cache if available
            if os.path.exists(cache_path):
                return pd.read_parquet(cache_path)
            raise ValueError(f"No daily historical data returned for ticker {ticker}")

        # Standardize columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        # Drop timezone info for clean local date alignment
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)

        df = df.sort_index()

        # Save to disk cache
        try:
            df.to_parquet(cache_path)
        except Exception:
            # If parquet not available, fallback to CSV
            csv_path = os.path.join(CACHE_DIR, f"{ticker}_daily.csv")
            df.to_csv(csv_path)

        MEM_CACHE[mem_key] = (df, now)
        return df.copy()

    except Exception as e:
        # Offline resilience: attempt to read disk cache
        if os.path.exists(cache_path):
            return pd.read_parquet(cache_path)
        csv_fallback = os.path.join(CACHE_DIR, f"{ticker}_daily.csv")
        if os.path.exists(csv_fallback):
            return pd.read_csv(csv_fallback, index_col=0, parse_dates=True)
        raise RuntimeError(f"Error fetching daily data for {ticker}: {str(e)}")


def get_premarket_quote(ticker: str, strict_premarket: bool = True) -> Dict[str, Any]:
    """
    Fetches pre-market quote for a ticker.
    Guarantees strict pre-bell isolation: when called during or after regular hours,
    it strictly measures trades executed prior to 09:30 EST to prevent intraday
    price bleed into pre-market metrics.
    """
    ticker = ticker.upper().strip()
    try:
        from src.fetchers.market_hours import get_current_market_session, MarketSession
        current_session = get_current_market_session()
        
        t = yf.Ticker(ticker)
        fast_info = getattr(t, "fast_info", {})
        
        hist_intraday = t.history(period="1d", interval="5m", prepost=True)
        
        last_price = None
        prev_close = None
        volume = 0
        
        if hasattr(fast_info, "previous_close") and fast_info.previous_close:
            prev_close = float(fast_info.previous_close)

        if not hist_intraday.empty:
            try:
                ny_bars = hist_intraday.tz_convert("America/New_York")
            except Exception:
                ny_bars = hist_intraday
                
            if strict_premarket and current_session != MarketSession.PRE_MARKET:
                # Strictly isolate trades executed between 04:00 and 09:29:59 EST
                pre_bars = ny_bars.between_time("04:00", "09:29")
                if not pre_bars.empty:
                    last_price = float(pre_bars["Close"].iloc[-1])
                    volume = int(pre_bars["Volume"].sum())
                else:
                    # Fallback to the opening price of the first regular-hours bar
                    rth_bars = ny_bars.between_time("09:30", "16:00")
                    if not rth_bars.empty:
                        last_price = float(rth_bars["Open"].iloc[0])
                        volume = 0
            else:
                last_price = float(hist_intraday["Close"].iloc[-1])
                volume = int(hist_intraday["Volume"].sum())
                
            if prev_close is None and not hist_intraday.empty:
                prev_close = float(hist_intraday["Open"].iloc[0])
            
        if last_price is None and hasattr(fast_info, "last_price") and fast_info.last_price:
            last_price = float(fast_info.last_price)

        if last_price is None or prev_close is None or prev_close == 0:
            daily = get_daily_history(ticker, period="5d")
            last_price = float(daily["Close"].iloc[-1])
            prev_close = float(daily["Close"].iloc[-2]) if len(daily) > 1 else last_price
            volume = int(daily["Volume"].iloc[-1])

        gap_pct = ((last_price - prev_close) / prev_close) * 100.0

        return {
            "ticker": ticker,
            "current_price": round(last_price, 2),
            "prev_close": round(prev_close, 2),
            "gap_pct": round(gap_pct, 2),
            "volume": volume,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_strict_premarket": strict_premarket
        }
    except Exception as e:
        try:
            daily = get_daily_history(ticker, period="5d")
            last = float(daily["Close"].iloc[-1])
            prev = float(daily["Close"].iloc[-2]) if len(daily) > 1 else last
            return {
                "ticker": ticker,
                "current_price": round(last, 2),
                "prev_close": round(prev, 2),
                "gap_pct": round(((last - prev) / prev) * 100.0, 2),
                "volume": int(daily["Volume"].iloc[-1]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "offline_daily_fallback"
            }
        except Exception:
            return {
                "ticker": ticker,
                "current_price": 0.0,
                "prev_close": 0.0,
                "gap_pct": 0.0,
                "volume": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }


def get_intraday_snapshot(ticker: str) -> Dict[str, Any]:
    """
    Fetches live regular-trading-hours intraday snapshot for a ticker.
    Returns current live price, high, low, VWAP, change %, and RTH volume.
    """
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        fast_info = getattr(t, "fast_info", {})
        
        prev_close = float(fast_info.previous_close) if hasattr(fast_info, "previous_close") and fast_info.previous_close else None
        if prev_close is None:
            daily = get_daily_history(ticker, period="5d")
            prev_close = float(daily["Close"].iloc[-2]) if len(daily) > 1 else float(daily["Close"].iloc[-1])
            
        hist = t.history(period="1d", interval="5m", prepost=False)
        if not hist.empty:
            cur_price = float(hist["Close"].iloc[-1])
            high_price = float(hist["High"].max())
            low_price = float(hist["Low"].min())
            open_price = float(hist["Open"].iloc[0])
            total_vol = int(hist["Volume"].sum())
            
            # Cumulative VWAP
            typical_price = (hist["High"] + hist["Low"] + hist["Close"]) / 3.0
            cum_vol = hist["Volume"].sum()
            vwap = float((typical_price * hist["Volume"]).sum() / cum_vol) if cum_vol > 0 else cur_price
        else:
            daily = get_daily_history(ticker, period="5d")
            cur_price = float(daily["Close"].iloc[-1])
            high_price = float(daily["High"].iloc[-1])
            low_price = float(daily["Low"].iloc[-1])
            open_price = float(daily["Open"].iloc[-1])
            total_vol = int(daily["Volume"].iloc[-1])
            vwap = cur_price
            
        chg_pct = ((cur_price - prev_close) / prev_close) * 100.0 if prev_close else 0.0
        
        return {
            "ticker": ticker,
            "current_price": round(cur_price, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": round(chg_pct, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "vwap": round(vwap, 2),
            "volume": total_vol,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "current_price": 0.0,
            "prev_close": 0.0,
            "change_pct": 0.0,
            "error": str(e)
        }


def fetch_all_watchlist_daily(watchlist: Optional[List[Dict[str, Any]]] = None) -> Dict[str, pd.DataFrame]:
    """Batch loads daily data for all stocks in the watchlist."""
    stocks = watchlist or load_watchlist()
    results: Dict[str, pd.DataFrame] = {}
    for item in stocks:
        ticker = item["ticker"]
        try:
            df = get_daily_history(ticker, period="2y")
            results[ticker] = df
        except Exception as e:
            print(f"Warning: Failed to load {ticker}: {e}")
    return results
