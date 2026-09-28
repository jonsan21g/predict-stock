import pytest
from src.fetchers.contracts_data import get_ticker_contract_signals, fetch_federal_contracts


def test_get_ticker_contract_signals_dell():
    # DELL is one of the largest DoD technology providers
    signals = get_ticker_contract_signals("DELL")
    assert isinstance(signals, dict)
    assert signals["ticker"] == "DELL"
    assert "contract_count" in signals
    assert "total_contract_value_usd" in signals
    assert "contract_score" in signals
    assert "is_defense_contract" in signals
    assert "top_agencies" in signals
    assert "recent_contracts" in signals

    # Validate DoD contracts presence
    if signals["contract_count"] > 0:
        assert signals["total_contract_value_usd"] > 100_000_000.0
        assert signals["has_major_contract"] is True
        assert signals["is_defense_contract"] is True
        assert signals["contract_score"] >= 80
        assert any("Defense" in str(a) for a in signals["top_agencies"])


def test_contracts_scoring_thresholds():
    from src.fetchers.contracts_data import get_ticker_contract_signals

    # Mock evaluation
    signals = get_ticker_contract_signals("UNKNOWN_TICKER_XYZ")
    assert signals["contract_count"] == 0
    assert signals["total_contract_value_usd"] == 0.0
    assert signals["has_major_contract"] is False
    assert signals["contract_score"] == 0
