"""
politician_data.py - Congressional STOCK Act disclosure scraper and scorer.
Ingests US House and Senate stock trades, identifies recent member accumulation,
and caches results locally to avoid unnecessary network overhead.
"""

import os
import re
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "congress_trades.json")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 43200  # 12 hours


def parse_trade_row(row_cells: List[str]) -> Optional[Dict[str, Any]]:
    """
    Parses a single row from CapitolTrades.
    Format typically: [Politician, Traded Issuer, Published, Traded, Filed After, Owner, Type, Size, Price, ...]
    """
    if len(row_cells) < 8:
        return None

    politician_raw = row_cells[0].strip()
    issuer_raw = row_cells[1].strip()
    published_date_str = row_cells[2].strip()
    traded_date_str = row_cells[3].strip()
    trade_type = row_cells[6].strip().lower()  # 'buy' or 'sell'
    trade_size = row_cells[7].strip()

    # Extract ticker from issuer string like 'Apple IncAAPL:US' or 'NVIDIA CorpNVDA:US'
    ticker_match = re.search(r'([A-Z]{1,5}):US', issuer_raw)
    ticker = ticker_match.group(1) if ticker_match else None
    if not ticker:
        tail_match = re.search(r'([A-Z]{1,5})$', issuer_raw)
        ticker = tail_match.group(1) if tail_match else None

    if not ticker:
        return None

    clean_date_str = re.sub(r'(\d{1,2})\s*([A-Za-z]+)\s*(\d{4})', r'\1 \2 \3', traded_date_str)
    try:
        for full_m, abbr in [("Sept", "Sep")]:
            clean_date_str = clean_date_str.replace(full_m, abbr)
        traded_dt = datetime.strptime(clean_date_str, "%d %b %Y").replace(tzinfo=timezone.utc)
        traded_date_iso = traded_dt.strftime("%Y-%m-%d")
    except Exception:
        traded_date_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "politician": politician_raw,
        "ticker": ticker.upper(),
        "issuer": issuer_raw,
        "type": "BUY" if "buy" in trade_type else "SELL",
        "size": trade_size,
        "traded_date": traded_date_iso,
        "published_date": published_date_str
    }


def fetch_congress_trades(max_pages: int = 5, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches recent Congressional trades from CapitolTrades with disk caching.
    """
    now = time.time()
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if now - mtime < CACHE_TTL:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    if cached_data:
                        return cached_data
        except Exception:
            pass

    trades: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        for page in range(1, max_pages + 1):
            url = f"https://www.capitoltrades.com/trades?page={page}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if not table:
                break
            trs = table.find_all("tr")
            for tr in trs[1:]:  # skip header
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                parsed = parse_trade_row(cells)
                if parsed:
                    trades.append(parsed)
            time.sleep(0.3)
    except Exception as e:
        print(f"Warning: Failed to fetch online congress data: {e}")

    if trades:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(trades, f, indent=2)
            return trades
        except Exception:
            return trades

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return []


def get_ticker_congress_signals(
    ticker: str,
    days: int = 45,
    all_trades: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes Congressional Smart-Money signals for a specific ticker over a recent window.
    """
    ticker = ticker.upper().strip()
    trades = all_trades if all_trades is not None else fetch_congress_trades()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    ticker_trades = [
        t for t in trades
        if t.get("ticker") == ticker and t.get("traded_date", "") >= cutoff_date
    ]

    buy_trades = [t for t in ticker_trades if t.get("type") == "BUY"]
    sell_trades = [t for t in ticker_trades if t.get("type") == "SELL"]

    politicians = list({t["politician"] for t in ticker_trades if "politician" in t})
    has_recent_buy = len(buy_trades) > 0

    return {
        "ticker": ticker,
        "window_days": days,
        "total_trades": len(ticker_trades),
        "buy_count": len(buy_trades),
        "sell_count": len(sell_trades),
        "has_recent_buy": has_recent_buy,
        "politicians": politicians[:5],
        "trades": ticker_trades
    }
