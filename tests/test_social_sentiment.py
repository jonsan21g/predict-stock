import pytest
from src.fetchers.social_sentiment import (
    score_text_sentiment,
    scan_politician_viral_buzz,
    get_ticker_social_sentiment
)


def test_score_text_sentiment():
    bull_text = "Nvidia surges to record high with strong revenue growth and massive breakout!"
    bull_score = score_text_sentiment(bull_text)
    assert bull_score > 0.3

    bear_text = "Stock plunges following earnings miss and analyst downgrade warning of losses"
    bear_score = score_text_sentiment(bear_text)
    assert bear_score < -0.3

    neutral_text = "The company scheduled its annual general meeting for next Tuesday."
    neutral_score = score_text_sentiment(neutral_text)
    assert neutral_score == 0.0


def test_scan_politician_viral_buzz_detection():
    # 1. Viral Pelosi & Congress copy-trading scenario
    viral_corpus = [
        "Nancy Pelosi just disclosed buying millions in NVDA calls! Everyone copy trade!",
        "Congress trading disclosures show massive tech accumulation",
        "Insider buy confirmed by director on open market"
    ]
    analysis = scan_politician_viral_buzz(viral_corpus)
    assert analysis["viral_politician_buzz"] is True
    assert analysis["politician_mentions_count"] >= 3
    assert "pelosi" in analysis["matched_buzz_keywords"]
    assert "congress" in analysis["matched_buzz_keywords"]
    assert "insider buy" in analysis["matched_buzz_keywords"]
    assert analysis["retail_hype_score"] >= 60
    assert analysis["is_pelosi_effect_active"] is True
    assert len(analysis["sample_buzz_quotes"]) > 0

    # Detailed Pelosi Effect assertions
    assert "pelosi_effect" in analysis
    pe = analysis["pelosi_effect"]
    assert pe["is_active"] is True
    assert pe["intensity"] in ["VIRAL_SURGE", "HIGH_VELOCITY"]
    assert "Nancy / Paul Pelosi" in pe["prominent_figures"]
    assert pe["primary_catalyst"] == "PELOSI_CONGRESSIONAL_COPYTRADE"
    assert len(pe["narrative_summary"]) > 20

    # 2. Generic, quiet scenario without smart-money buzz
    quiet_corpus = [
        "Quarterly balance sheet updates released today.",
        "Trading volume remains steady heading into the weekend."
    ]
    quiet_analysis = scan_politician_viral_buzz(quiet_corpus)
    assert quiet_analysis["viral_politician_buzz"] is False
    assert quiet_analysis["politician_mentions_count"] == 0
    assert quiet_analysis["retail_hype_score"] == 0
    assert quiet_analysis["is_pelosi_effect_active"] is False
    assert quiet_analysis["pelosi_effect"]["is_active"] is False


def test_get_ticker_social_sentiment_structure():
    res = get_ticker_social_sentiment("NVDA")
    assert isinstance(res, dict)
    assert res["ticker"] == "NVDA"
    assert "article_count" in res
    assert "social_message_count" in res
    assert "total_volume" in res
    assert "sentiment_score" in res
    assert res["sentiment_label"] in ["BULLISH", "BEARISH", "NEUTRAL"]
    assert "buzz_zscore" in res
    assert "viral_politician_buzz" in res
    assert "retail_hype_score" in res
    assert "is_pelosi_effect_active" in res
    assert "pelosi_effect" in res
