"""
insider_data.py - Corporate Insider Transaction Parser and Scorer (SEC Form 4).
Filters out routine option grants, detects open-market cluster purchases,
and scores executive accumulation conviction.
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 86400  # 24 hours


def get_insider_transactions(ticker: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches official insider transactions from SEC Form 4 via yfinance with local caching.
    """
    ticker = ticker.upper().strip()
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_insiders.json")
    now = time.time()

    if not force_refresh and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if now - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    transactions: List[Dict[str, Any]] = []
    try:
        t = yf.Ticker(ticker)
        df_insiders = t.insider_transactions
        if df_insiders is not None and not df_insiders.empty:
            for _, row in df_insiders.iterrows():
                raw_text = str(row.get("Text", "")).strip()
                insider_name = str(row.get("Insider", "")).strip()
                position = str(row.get("Position", "")).strip()
                shares = int(row.get("Shares", 0)) if pd.notna(row.get("Shares")) else 0
                value = float(row.get("Value", 0)) if pd.notna(row.get("Value")) else 0.0

                start_date = row.get("Start Date")
                if pd.notna(start_date):
                    if isinstance(start_date, (pd.Timestamp, datetime)):
                        date_str = start_date.strftime("%Y-%m-%d")
                    else:
                        date_str = str(start_date)[:10]
                else:
                    date_str = ""

                text_lower = raw_text.lower()
                if "purchase" in text_lower or "buy" in text_lower:
                    ttype = "BUY"
                elif "sale" in text_lower or "sold" in text_lower:
                    ttype = "SELL"
                elif "grant" in text_lower or "award" in text_lower:
                    ttype = "GRANT"
                elif "option" in text_lower or "exercise" in text_lower:
                    ttype = "OPTION"
                else:
                    ttype = "OTHER"

                transactions.append({
                    "date": date_str,
                    "insider": insider_name,
                    "position": position,
                    "type": ttype,
                    "shares": shares,
                    "value_usd": value,
                    "text": raw_text
                })
    except Exception as e:
        print(f"Warning: Failed to fetch insider transactions for {ticker}: {e}")

    if transactions:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(transactions, f, indent=2)
        except Exception:
            pass

    return transactions


def get_insider_signals(ticker: str, days: int = 45) -> Dict[str, Any]:
    """
    Evaluates insider sentiment for a ticker over the specified time window.
    Detects C-suite buying, cluster buying, and net accumulation.
    """
    transactions = get_insider_transactions(ticker)
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    recent_tx = [t for t in transactions if t.get("date", "") >= cutoff_date]
    buys = [t for t in recent_tx if t.get("type") == "BUY"]
    sells = [t for t in recent_tx if t.get("type") == "SELL"]

    buy_shares = sum(t.get("shares", 0) for t in buys)
    sell_shares = sum(t.get("shares", 0) for t in sells)
    buy_value = sum(t.get("value_usd", 0.0) for t in buys)

    c_suite_keywords = ["chief", "ceo", "cfo", "coo", "director", "president"]
    c_suite_buyers = list({
        f"{t.get('insider')} ({t.get('position')})"
        for t in buys
        if any(kw in t.get("position", "").lower() for kw in c_suite_keywords)
    })

    unique_buyers = len({t.get("insider") for t in buys})
    has_cluster_buy = unique_buyers >= 2

    score = 0
    if len(buys) > 0:
        score += 40
    if has_cluster_buy:
        score += 30
    if len(c_suite_buyers) > 0:
        score += 20
    if buy_value > 500000:
        score += 10
    score = min(score, 100)

    return {
        "ticker": ticker,
        "window_days": days,
        "buy_count": len(buys),
        "sell_count": len(sells),
        "total_buy_value_usd": round(buy_value, 2),
        "net_shares": buy_shares - sell_shares,
        "unique_buyers": unique_buyers,
        "has_cluster_buy": has_cluster_buy,
        "has_recent_buy": len(buys) > 0,
        "c_suite_buyers": c_suite_buyers,
        "insider_score": score,
        "recent_buys": buys[:5]
    }
