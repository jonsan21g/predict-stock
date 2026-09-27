"""
social_sentiment.py - Financial News Sentiment and Buzz Velocity Tracker.
Evaluates domain-specific bullish/bearish polarity, mention volume, and news acceleration
without external API keys or cloud LLM costs.
"""

import os
import json
import time
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 14400  # 4 hours

# Domain-specific financial sentiment lexicons
BULL_WORDS = {
    "surge", "surges", "surging", "rally", "rallies", "rallying", "soar", "soars", "soaring",
    "jump", "jumps", "jumped", "beat", "beats", "beating", "outperform", "outperformed",
    "upgrade", "upgrades", "upgraded", "breakout", "bullish", "record", "gain", "gains",
    "gaining", "boost", "boosts", "boosted", "high", "highs", "profit", "profits", "profitable",
    "growth", "expand", "expansion", "dividend", "buy", "buying", "accumulate", "catalyst"
}

BEAR_WORDS = {
    "plunge", "plunges", "plunging", "drop", "drops", "dropped", "slump", "slumps",
    "fall", "falls", "falling", "sink", "sinks", "sinking", "miss", "misses", "missed",
    "downgrade", "downgrades", "downgraded", "bearish", "crash", "loss", "losses",
    "decline", "declines", "declining", "risk", "risks", "probe", "investigation",
    "selloff", "dump", "dumped", "cut", "cuts", "cutting", "struggle", "struggles", "warning"
}


def score_text_sentiment(text: str) -> float:
    """
    Computes sentiment polarity between -1.0 (very bearish) and +1.0 (very bullish).
    Returns 0.0 if neutral or empty.
    """
    if not text:
        return 0.0
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    if not words:
        return 0.0

    bull_count = sum(1 for w in words if w in BULL_WORDS)
    bear_count = sum(1 for w in words if w in BEAR_WORDS)
    total_matches = bull_count + bear_count

    if total_matches == 0:
        return 0.0
    return round((bull_count - bear_count) / total_matches, 3)


def get_ticker_social_sentiment(ticker: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Gathers financial sentiment and buzz velocity for a ticker with local disk caching.
    """
    ticker = ticker.upper().strip()
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_sentiment.json")
    now = time.time()

    if not force_refresh and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if now - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    headlines: List[str] = []
    sentiment_scores: List[float] = []

    try:
        t = yf.Ticker(ticker)
        raw_news = getattr(t, "news", []) or []
        for item in raw_news:
            content = item.get("content", {})
            title = content.get("title", "") or item.get("title", "")
            summary = content.get("summary", "") or ""
            combined = f"{title}. {summary}".strip()
            if title:
                headlines.append(title)
                score = score_text_sentiment(combined)
                sentiment_scores.append(score)
    except Exception as e:
        print(f"Warning: Failed to fetch news for {ticker}: {e}")

    article_count = len(headlines)
    avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 3) if sentiment_scores else 0.0

    baseline = 4.0
    buzz_zscore = round((article_count - baseline) / 2.0, 2)

    if avg_sentiment >= 0.2:
        label = "BULLISH"
    elif avg_sentiment <= -0.2:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    result = {
        "ticker": ticker,
        "article_count": article_count,
        "sentiment_score": avg_sentiment,
        "sentiment_label": label,
        "buzz_zscore": buzz_zscore,
        "top_headlines": headlines[:3],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result
