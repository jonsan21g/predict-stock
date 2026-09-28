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
                msg_id = m.get("id")
                username = m.get("user", {}).get("username", "trader") if m.get("user") else "trader"
                msg_url = f"https://stocktwits.com/message/{msg_id}" if msg_id else f"https://stocktwits.com/symbol/{ticker}"
                if body:
                    messages.append({
                        "body": body,
                        "sentiment": user_sentiment,
                        "created_at": created_at,
                        "id": msg_id,
                        "user": username,
                        "url": msg_url,
                        "source": "StockTwits"
                    })
    except Exception:
        pass
    return messages


def scan_politician_viral_buzz(text_corpus: List[Any], ticker: Optional[str] = None) -> Dict[str, Any]:
    """
    Scans a combined corpus of social messages and news headlines for politician and
    insider accumulation buzz (the 'Pelosi Effect'). Computes in-depth catalyst classification,
    prominent figures mentioned, lifecycle stage, retail hype score (0-100), and narrative summary.
    Filters out multi-ticker pump spam blasts (>= 4 cashtags) and explicit symbol mismatches.
    """
    matched_quotes_str: List[str] = []
    matched_quotes_obj: List[Dict[str, Any]] = []
    matched_keywords_set = set()
    total_mentions = 0
    all_raw_texts: List[str] = []

    for item in text_corpus:
        if isinstance(item, dict):
            text = item.get("text") or item.get("body") or item.get("title") or ""
            item_url = item.get("url")
            item_source = item.get("source", "Social Stream")
            item_author = item.get("author") or item.get("user") or ""
        else:
            text = str(item)
            item_url = None
            item_source = "Social Stream"
            item_author = ""

        if not text:
            continue

        all_raw_texts.append(text)
        text_lower = text.lower()
        found_in_text = [kw for kw in POLITICIAN_VIRAL_KEYWORDS if kw in text_lower]
        if not found_in_text:
            continue

        # Spam Filter 1: Multi-ticker cashtag spam blast (>= 4 cashtags e.g. $ADI $MPWR $MTSI $CRUS)
        cashtags = re.findall(r'\$[A-Z]{1,5}\b', text)
        if len(cashtags) >= 4:
            continue

        # Spam Filter 2: Explicit mismatch where post specifies another stock e.g. "Symbol MX"
        if ticker:
            sym_match = re.search(r'\b(symbol|ticker)\s+([A-Z]{1,5})\b', text, re.IGNORECASE)
            if sym_match and sym_match.group(2).upper() != ticker.upper():
                continue

        total_mentions += 1
        matched_keywords_set.update(found_in_text)
        clean_sample = text.replace("\n", " ").strip()
        if len(clean_sample) > 130:
            clean_sample = clean_sample[:127] + "..."

        final_url = item_url or (f"https://stocktwits.com/symbol/{ticker}" if ticker else "https://stocktwits.com")
        matched_quotes_str.append(clean_sample)
        matched_quotes_obj.append({
            "text": clean_sample,
            "url": final_url,
            "source": item_source,
            "author": item_author
        })

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
        if "whale" in matched_keywords_set or "copy trade" in matched_keywords_set or "copytrade" in matched_keywords_set:
            hype_score += 10
    hype_score = min(100, hype_score)

    is_pelosi_effect = hype_score >= 60

    # 1. Identify Prominent Political & Executive Figures Mentioned
    prominent_figures = []
    text_blob = " ".join(all_raw_texts).lower()
    if "pelosi" in text_blob:
        prominent_figures.append("Nancy / Paul Pelosi")
    if "rick allen" in text_blob:
        prominent_figures.append("Rep. Rick Allen (House Energy & Commerce)")
    if "mccaul" in text_blob:
        prominent_figures.append("Rep. Michael McCaul (Foreign Affairs / CHIPS Act)")
    if "ro khanna" in text_blob:
        prominent_figures.append("Rep. Ro Khanna (Armed Services)")
    if "tuberville" in text_blob:
        prominent_figures.append("Sen. Tommy Tuberville (Armed Services)")
    if "ceo" in text_blob or "chief executive" in text_blob:
        prominent_figures.append("Corporate CEO / C-Suite")
    if "director" in text_blob or "board member" in text_blob:
        prominent_figures.append("Board of Directors")

    # 2. Classify Primary Catalyst
    if "pelosi" in matched_keywords_set:
        primary_catalyst = "PELOSI_CONGRESSIONAL_COPYTRADE"
    elif "congress" in matched_keywords_set or "senator" in matched_keywords_set or "stock act" in matched_keywords_set or "capitol" in matched_keywords_set:
        primary_catalyst = "CAPITOL_HILL_DISCLOSURE"
    elif "insider buy" in matched_keywords_set or "cluster buy" in matched_keywords_set or "ceo bought" in matched_keywords_set:
        primary_catalyst = "C_SUITE_INSIDER_WHALE_ACCUMULATION"
    elif "whale" in matched_keywords_set or "copy trade" in matched_keywords_set or "copytrade" in matched_keywords_set:
        primary_catalyst = "RETAIL_HERD_WHALE_COPYTRADE"
    else:
        primary_catalyst = "ORGANIC_MOMENTUM_DISCUSSION" if is_viral else "DORMANT"

    # 3. Classify Intensity & Lifecycle
    if hype_score >= 80:
        intensity = "VIRAL_SURGE"
        lifecycle_stage = "PEAK_HERD_EXPANSION"
    elif hype_score >= 60:
        intensity = "HIGH_VELOCITY"
        lifecycle_stage = "IGNITION_ACCELERATION"
    elif hype_score >= 35:
        intensity = "MODERATE_INTEREST"
        lifecycle_stage = "EMERGING_AWARENESS"
    else:
        intensity = "QUIET / DORMANT"
        lifecycle_stage = "DORMANT"

    # 4. Generate Narrative Summary
    if is_pelosi_effect:
        cat_title = primary_catalyst.replace("_", " ").title()
        figures_txt = f" citing {', '.join(prominent_figures)}" if prominent_figures else ""
        narrative = (
            f"Active Pelosi Effect ({intensity} - Hype Score: {hype_score}/100): "
            f"Retail social streams are actively circulating {cat_title}{figures_txt}. "
            f"Discussion demonstrates rapid copy-trading accumulation with strong bullish bias."
        )
    elif is_viral:
        keywords_sample = ", ".join(list(matched_keywords_set)[:3])
        narrative = (
            f"Emerging Smart-Money Chatter ({intensity} - Hype Score: {hype_score}/100): "
            f"Traders are discussing smart-money catalysts ({keywords_sample}). "
            f"Retail awareness is building but remains below the peak viral copy-trading herd threshold."
        )
    else:
        narrative = "No active politician copy-trading or viral smart-money chatter detected on social streams."

    pelosi_effect_details = {
        "is_active": is_pelosi_effect,
        "intensity": intensity,
        "hype_score": hype_score,
        "primary_catalyst": primary_catalyst,
        "prominent_figures": prominent_figures,
        "lifecycle_stage": lifecycle_stage,
        "narrative_summary": narrative,
        "matched_keywords": sorted(list(matched_keywords_set)),
        "mentions_count": total_mentions,
        "verbatim_quotes": matched_quotes_obj[:3]
    }

    return {
        "viral_politician_buzz": is_viral,
        "politician_mentions_count": total_mentions,
        "matched_buzz_keywords": sorted(list(matched_keywords_set)),
        "sample_buzz_quotes": matched_quotes_str[:3],
        "retail_hype_score": hype_score,
        "is_pelosi_effect_active": is_pelosi_effect,
        "pelosi_effect": pelosi_effect_details
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
                    if "pelosi_effect" in cached:
                        return cached
        except Exception:
            pass

    headlines: List[str] = []
    social_texts: List[str] = []
    sentiment_scores: List[float] = []
    corpus_items: List[Dict[str, Any]] = []

    # 1. Fetch official financial news via yfinance
    try:
        t = yf.Ticker(ticker)
        raw_news = getattr(t, "news", []) or []
        for item in raw_news:
            content = item.get("content", {})
            title = content.get("title", "") or item.get("title", "")
            summary = content.get("summary", "") or ""
            link = item.get("link") or (content.get("canonicalUrl", {}) or {}).get("url") or f"https://finance.yahoo.com/quote/{ticker}/news/"
            pub = item.get("publisher") or (content.get("provider", {}) or {}).get("displayName") or "Yahoo Finance"
            combined = f"{title}. {summary}".strip()
            if title:
                headlines.append(title)
                score = score_text_sentiment(combined)
                sentiment_scores.append(score)
                corpus_items.append({
                    "text": combined,
                    "title": title,
                    "url": link,
                    "source": f"News ({pub})",
                    "author": pub
                })
    except Exception as e:
        print(f"Warning: Failed to fetch news for {ticker}: {e}")

    # 2. Fetch live retail social stream messages via StockTwits
    stocktwits_msgs = fetch_stocktwits_feed(ticker)
    for m in stocktwits_msgs:
        body = m["body"]
        social_texts.append(body)
        corpus_items.append({
            "text": body,
            "title": body,
            "url": m.get("url") or f"https://stocktwits.com/symbol/{ticker}",
            "source": "StockTwits",
            "author": m.get("user") or "trader"
        })
        
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
    viral_analysis = scan_politician_viral_buzz(corpus_items, ticker=ticker)

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
        "pelosi_effect": viral_analysis["pelosi_effect"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result
