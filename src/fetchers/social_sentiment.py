"""
social_sentiment.py - Financial News Sentiment, Retail Social Streams, and Politician Viral Buzz Tracker.
Evaluates domain-specific bullish/bearish polarity, mention velocity, and viral politician/insider
copy-trading buzz (the 'Pelosi Effect') across financial news and retail streams without paid API costs.
"""

import os
import json
import time
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 7200  # 2 hours

# ---------------------------------------------------------------------
# Domain-Specific Financial Sentiment Lexicons
# ---------------------------------------------------------------------
BULL_WORDS = {
    "surge", "surges", "surging", "rally", "rallies", "rallying", "soar", "soars", "soaring",
    "jump", "jumps", "jumped", "beat", "beats", "beating", "outperform", "outperformed",
    "upgrade", "upgrades", "upgraded", "breakout", "bullish", "record", "gain", "gains",
    "gaining", "boost", "boosts", "boosted", "high", "highs", "profit", "profits", "profitable",
    "growth", "expand", "expansion", "dividend", "buy", "buying", "accumulate", "catalyst",
    "moon", "calls", "call", "yolo", "long", "rocket", "squeeze"
}

BEAR_WORDS = {
    "plunge", "plunges", "plunging", "drop", "drops", "dropped", "slump", "slumps",
    "fall", "falls", "falling", "sink", "sinks", "sinking", "miss", "misses", "missed",
    "downgrade", "downgrades", "downgraded", "bearish", "crash", "loss", "losses",
    "decline", "declines", "declining", "risk", "risks", "probe", "investigation",
    "selloff", "dump", "dumped", "cut", "cuts", "cutting", "struggle", "struggles", "warning",
    "puts", "put", "short", "tank"
}

# Targeted Politician & Smart-Money Retail Buzz Lexicon (The "Pelosi Effect")
POLITICIAN_VIRAL_KEYWORDS = {
    "pelosi", "congress", "senator", "representative", "stock act",
    "capitol", "quiver", "unusual whales", "insider buy", "insider buying",
    "ceo bought", "director bought", "form 4", "cluster buy", "rick allen",
    "mccaul", "politician", "copytrade", "copy trade", "copy-trade", "whale"
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


def fetch_stocktwits_feed(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetches the 30 most recent real-time stream messages for a ticker from StockTwits.
    Zero-cost public stream endpoint with resilient timeout handling.
    """
    ticker = ticker.upper().strip()
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    messages: List[Dict[str, Any]] = []
    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            data = r.json()
            raw_msgs = data.get("messages", [])
            for m in raw_msgs:
                body = m.get("body", "").strip()
                entities = m.get("entities", {})
                sentiment_info = entities.get("sentiment", {})
                user_sentiment = sentiment_info.get("basic") if sentiment_info else None
                created_at = m.get("created_at", "")
                if body:
                    messages.append({
                        "body": body,
                        "sentiment": user_sentiment,
                        "created_at": created_at
                    })
    except Exception:
        pass
    return messages


def scan_politician_viral_buzz(text_corpus: List[str]) -> Dict[str, Any]:
    """
    Scans a combined corpus of social messages and news headlines for politician and
    insider accumulation buzz (the 'Pelosi Effect'). Computes retail hype score (0-100).
    """
    matched_quotes: List[str] = []
    matched_keywords_set = set()
    total_mentions = 0

    for text in text_corpus:
        text_lower = text.lower()
        found_in_text = [kw for kw in POLITICIAN_VIRAL_KEYWORDS if kw in text_lower]
        if found_in_text:
            total_mentions += 1
            matched_keywords_set.update(found_in_text)
            clean_sample = text.replace("\n", " ").strip()
            if len(clean_sample) > 120:
                clean_sample = clean_sample[:117] + "..."
            matched_quotes.append(clean_sample)

    is_viral = total_mentions >= 1
    
    # Calculate Retail Hype Score (0 - 100)
    hype_score = 0
    if is_viral:
        hype_score += 40  # Base viral catalyst
        hype_score += min(30, total_mentions * 15)  # Mention velocity
        if "pelosi" in matched_keywords_set:
            hype_score += 20  # Massive "Pelosi Effect" multiplier
        if "insider buy" in matched_keywords_set or "cluster buy" in matched_keywords_set:
            hype_score += 15
    hype_score = min(100, hype_score)

    is_pelosi_effect = hype_score >= 60

    return {
        "viral_politician_buzz": is_viral,
        "politician_mentions_count": total_mentions,
        "matched_buzz_keywords": sorted(list(matched_keywords_set)),
        "sample_buzz_quotes": matched_quotes[:3],
        "retail_hype_score": hype_score,
        "is_pelosi_effect_active": is_pelosi_effect
    }


def get_ticker_social_sentiment(ticker: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Gathers financial sentiment, retail stream velocity, and targeted politician buzz
    for a ticker with local disk caching.
    """
    ticker = ticker.upper().strip()
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_sentiment.json")
    now = time.time()

    if not force_refresh and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if now - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    # Backwards compatibility check
                    if "viral_politician_buzz" in cached:
                        return cached
        except Exception:
            pass

    headlines: List[str] = []
    social_texts: List[str] = []
    sentiment_scores: List[float] = []

    # 1. Fetch official financial news via yfinance
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

    # 2. Fetch live retail social stream messages via StockTwits
    stocktwits_msgs = fetch_stocktwits_feed(ticker)
    for m in stocktwits_msgs:
        body = m["body"]
        social_texts.append(body)
        
        # User explicit sentiment or lex analysis
        if m.get("sentiment") == "Bullish":
            sentiment_scores.append(0.8)
        elif m.get("sentiment") == "Bearish":
            sentiment_scores.append(-0.8)
        else:
            score = score_text_sentiment(body)
            if score != 0.0:
                sentiment_scores.append(score)

    # 3. Detect Targeted Politician & Smart-Money Viral Buzz
    combined_corpus = headlines + social_texts
    viral_analysis = scan_politician_viral_buzz(combined_corpus)

    article_count = len(headlines)
    social_count = len(social_texts)
    avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 3) if sentiment_scores else 0.0

    # Calculate Buzz Z-Score (baseline volume ~10 items)
    total_volume = article_count + social_count
    baseline = 10.0
    buzz_zscore = round((total_volume - baseline) / 4.0, 2)

    if avg_sentiment >= 0.15:
        label = "BULLISH"
    elif avg_sentiment <= -0.15:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    result = {
        "ticker": ticker,
        "article_count": article_count,
        "social_message_count": social_count,
        "total_volume": total_volume,
        "sentiment_score": avg_sentiment,
        "sentiment_label": label,
        "buzz_zscore": buzz_zscore,
        "top_headlines": headlines[:3],
        "viral_politician_buzz": viral_analysis["viral_politician_buzz"],
        "politician_mentions_count": viral_analysis["politician_mentions_count"],
        "matched_buzz_keywords": viral_analysis["matched_buzz_keywords"],
        "sample_buzz_quotes": viral_analysis["sample_buzz_quotes"],
        "retail_hype_score": viral_analysis["retail_hype_score"],
        "is_pelosi_effect_active": viral_analysis["is_pelosi_effect_active"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result
