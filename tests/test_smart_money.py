import pytest
from src.fetchers.politician_data import parse_trade_row, get_ticker_congress_signals
from src.fetchers.insider_data import get_insider_transactions, get_insider_signals


def test_parse_trade_row():
    sample_cells = [
        "Pete SessionsRepublicanHouseTX",
        "Apple IncAAPL:US",
        "23 Sept2026",
        "22 Sept2026",
        "days0",
        "Spouse",
        "sell",
        "100K-250K",
        "$339.75",
        "Goto trade detail page."
    ]
    parsed = parse_trade_row(sample_cells)
    assert parsed is not None
    assert parsed["ticker"] == "AAPL"
    assert parsed["type"] == "SELL"
    assert parsed["politician"] == "Pete SessionsRepublicanHouseTX"
    assert parsed["traded_date"] == "2026-09-22"

    sample_buy = [
        "Nancy PelosiDemocratHouseCA",
        "NVIDIA CorpNVDA:US",
        "15 Sept2026",
        "10 Sept2026",
        "days5",
        "Spouse",
        "buy",
        "1M-5M",
        "$120.00",
        ""
    ]
    parsed_buy = parse_trade_row(sample_buy)
    assert parsed_buy is not None
    assert parsed_buy["ticker"] == "NVDA"
    assert parsed_buy["type"] == "BUY"
    assert parsed_buy["traded_date"] == "2026-09-10"


def test_congress_signals_with_mock():
    from datetime import datetime, timezone, timedelta
    d5 = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    d10 = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    d15 = (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d")

    mock_trades = [
        {
            "politician": "Nancy Pelosi",
            "ticker": "NVDA",
            "type": "BUY",
            "size": "1M-5M",
            "traded_date": d5
        },
        {
            "politician": "Michael McCaul",
            "ticker": "NVDA",
            "type": "BUY",
            "size": "250K-500K",
            "traded_date": d10
        },
        {
            "politician": "Josh Gottheimer",
            "ticker": "MSFT",
            "type": "SELL",
            "size": "15K-50K",
            "traded_date": d15
        }
    ]

    nvda_signals = get_ticker_congress_signals("NVDA", days=30, all_trades=mock_trades)
    assert nvda_signals["buy_count"] == 2
    assert nvda_signals["has_recent_buy"] is True
    assert nvda_signals["has_jurisdiction_match"] is True
    assert nvda_signals["congress_score"] >= 50
    assert len(nvda_signals["matched_committees"]) >= 1
    assert len(nvda_signals["politicians"]) == 2

    msft_signals = get_ticker_congress_signals("MSFT", days=30, all_trades=mock_trades)
    assert msft_signals["buy_count"] == 0
    assert msft_signals["sell_count"] == 1
    assert msft_signals["has_recent_buy"] is False
    assert msft_signals["has_jurisdiction_match"] is False


def test_congress_committee_jurisdiction_matching():
    from src.fetchers.politician_data import get_politician_committee_info, normalize_politician_name

    assert normalize_politician_name("Rick AllenRepublicanHouseGA") == "Rick Allen"
    assert normalize_politician_name("Pete SessionsRepublicanHouseTX") == "Pete Sessions"

    # Rick Allen sits on Energy and Commerce (CHIPS Act & Telecom)
    allen_info = get_politician_committee_info("Rick AllenRepublicanHouseGA")
    assert allen_info["jurisdiction_match"] is True
    assert "Energy and Commerce" in allen_info["matched_alpha_committees"]
    assert allen_info["jurisdiction_weight"] == 2.5

    # Ro Khanna sits on Armed Services (Cyber & Defense Tech)
    khanna_info = get_politician_committee_info("Ro Khanna")
    assert khanna_info["jurisdiction_match"] is True
    assert "Armed Services" in khanna_info["matched_alpha_committees"]

    # Pete Sessions sits on Financial Services / Oversight (Not direct tech/defense oversight)
    sessions_info = get_politician_committee_info("Pete SessionsRepublicanHouseTX")
    assert sessions_info["jurisdiction_match"] is False
    assert sessions_info["jurisdiction_weight"] == 1.0


def test_insider_transactions_live():
    txs = get_insider_transactions("NVDA")
    assert isinstance(txs, list)
    if txs:
        assert "date" in txs[0]
        assert "type" in txs[0]
        assert "insider" in txs[0]

    signals = get_insider_signals("NVDA", days=180)
    assert isinstance(signals, dict)
    assert "ticker" in signals
    assert "buy_count" in signals
    assert "sell_count" in signals
    assert "insider_score" in signals
