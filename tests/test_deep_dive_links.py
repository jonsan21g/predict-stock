"""
test_deep_dive_links.py - Verification for forensic deep links, scrapers, and 4-Pillar nomenclature.
Ensures zero broken searches, accurate SEC Form 4 purchase filtering, verified USAspending permalinks,
and multi-cashtag spam filtering for social sentiment streams.
"""

import pytest
from src.fetchers.politician_data import parse_trade_row, get_ticker_congress_signals
from src.fetchers.insider_data import get_insider_signals
from src.fetchers.contracts_data import get_ticker_contract_signals, fetch_federal_contracts
from src.fetchers.social_sentiment import scan_politician_viral_buzz


def test_congressional_extraction_and_quiver_urls():
    # 1. Valid ticker parsing
    valid_row = [
        "Nancy PelosiDemocratHouseCA",
        "NVIDIA CorpNVDA:US",
        "10 Sep 2026",
        "02 Sep 2026",
        "8 days",
        "Spouse",
        "Buy",
        "$1,000,001–$5,000,000"
    ]
    parsed = parse_trade_row(valid_row)
    assert parsed is not None
    assert parsed["ticker"] == "NVDA"
    assert parsed["type"] == "BUY"
    assert "quiverquant.com/congresstrading/stock/NVDA" in parsed["quiver_ticker_url"]
    assert "quiverquant.com/congresstrading/politician/Nancy%20Pelosi" in parsed["quiver_politician_url"]

    # 2. Private LLC with N/A ticker must NOT extract 'A'
    na_llc_row = [
        "Richard BlumenthalDemocratSenateCT",
        "NOT FADE AWAY LLCN/A",
        "11 Sep 2026",
        "11 Sep 2026",
        "0 days",
        "Self",
        "Buy",
        "1K–15K"
    ]
    na_parsed = parse_trade_row(na_llc_row)
    assert na_parsed is None, "Private LLC ending in N/A must not be misparsed as ticker 'A'"

    # 3. Signals dict must include verified portal URLs
    signals = get_ticker_congress_signals("NVDA")
    assert "quiver_stock_url" in signals
    assert "capitoltrades_url" in signals
    assert "house_disclosure_url" in signals
    assert signals["quiver_stock_url"] == "https://www.quiverquant.com/congresstrading/stock/NVDA"


def test_insider_openinsider_filtered_urls():
    signals = get_insider_signals("NVDA")
    assert "openinsider_purchases_url" in signals
    assert "openinsider_all_url" in signals
    assert "sec_edgar_url" in signals

    # Ensure openinsider_purchases_url isolates purchases via Code P and xp=1
    assert "tc=P" in signals["openinsider_purchases_url"]
    assert "xp=1" in signals["openinsider_purchases_url"]
    assert "s=NVDA" in signals["openinsider_purchases_url"]


def test_federal_contracts_permalinks():
    contracts = fetch_federal_contracts("DELL")
    assert isinstance(contracts, list)
    if contracts:
        c = contracts[0]
        assert "award_url" in c
        assert "award_id" in c
        assert c["award_url"].startswith("https://www.usaspending.gov/")

    signals = get_ticker_contract_signals("DELL")
    assert "usaspending_search_url" in signals
    assert "usaspending_recipient_url" in signals


def test_social_sentiment_spam_filter_and_quote_permalinks():
    # 1. Multi-cashtag spam blast (>= 4 cashtags) must be rejected
    spam_corpus = [
        "$ADI $MPWR $MTSI $CRUS Great insider buy from Magnachip CEO for 100K shares filed last Friday Symbol MX",
        "$NVDA $ON $ADI $SPCX Great insider buy from Maganchip CEO for 100K shares filed last Friday - Symbol MX"
    ]
    spam_analysis = scan_politician_viral_buzz(spam_corpus, ticker="ADI")
    assert spam_analysis["viral_politician_buzz"] is False
    assert len(spam_analysis["sample_buzz_quotes"]) == 0
    assert len(spam_analysis["pelosi_effect"]["verbatim_quotes"]) == 0

    # 2. Genuine single-stock catalyst must be accepted with structured URL
    genuine_corpus = [
        {
            "text": "Nancy Pelosi just disclosed massive calls purchase on $NVDA! Retail traders loading calls.",
            "url": "https://stocktwits.com/message/586745123",
            "source": "StockTwits",
            "author": "tech_trader"
        }
    ]
    genuine_analysis = scan_politician_viral_buzz(genuine_corpus, ticker="NVDA")
    assert genuine_analysis["viral_politician_buzz"] is True
    assert genuine_analysis["pelosi_effect"]["is_active"] is True
    quotes = genuine_analysis["pelosi_effect"]["verbatim_quotes"]
    assert len(quotes) == 1
    assert quotes[0]["url"] == "https://stocktwits.com/message/586745123"
    assert quotes[0]["source"] == "StockTwits"
