import os
import pytest
from src.game.duel import (
    initialize_game_state,
    get_live_duel_status,
    execute_player_order,
    bot_evaluate_turn,
    INITIAL_BANKROLL,
    MATCH_END_ISO,
    GAME_ID,
    is_ticker_quarantined,
    add_ticker_to_quarantine,
    is_macro_regime_bullish,
    calculate_conviction_allocation,
    MINIMUM_BOT_TRADE_CASH_THRESHOLD
)


@pytest.fixture(autouse=True)
def reset_game(tmp_path, monkeypatch):
    test_game_file = str(tmp_path / "test_game_state.json")
    monkeypatch.setenv("WAVE_RIDER_GAME_FILE", test_game_file)
    initialize_game_state(force_reset=True)
    yield


def test_initial_game_state():
    status = get_live_duel_status(live_prices={})
    assert status["player"]["cash"] == INITIAL_BANKROLL
    assert status["player"]["net_equity"] == INITIAL_BANKROLL
    assert status["bot"]["cash"] == INITIAL_BANKROLL
    assert status["bot"]["net_equity"] == INITIAL_BANKROLL
    assert status["leader"] == "TIED"
    assert "Remaining" in status["countdown"] or "Ends" in status["countdown"] or "FINISHED" in status["countdown"]


def test_player_order_buy_and_sell():
    # Buy 10 shares of NVDA at fixed $200.00
    buy_res = execute_player_order(action="BUY", ticker="NVDA", shares=10, force_price=200.0)
    assert buy_res["status"] == "SUCCESS"
    assert buy_res["action"] == "BUY"

    status = get_live_duel_status(live_prices={"NVDA": 220.0})
    assert status["player"]["cash"] == INITIAL_BANKROLL - 2000.0
    assert len(status["player"]["positions"]) == 1
    assert status["player"]["positions"][0]["ticker"] == "NVDA"
    assert status["player"]["positions"][0]["shares"] == 10
    # Price increased to 220 -> market value 2200, net equity 30200
    assert status["player"]["stock_value"] == 2200.0
    assert status["player"]["net_equity"] == 30200.0
    assert status["player"]["total_pnl"] == 200.0
    assert status["leader"] == "PLAYER"

    # Sell 5 shares of NVDA at $220.0
    sell_res = execute_player_order(action="SELL", ticker="NVDA", shares=5, force_price=220.0)
    assert sell_res["status"] == "SUCCESS"
    assert sell_res["action"] == "SELL"

    status2 = get_live_duel_status(live_prices={"NVDA": 220.0})
    assert status2["player"]["positions"][0]["shares"] == 5
    assert status2["player"]["cash"] == (INITIAL_BANKROLL - 2000.0) + 1100.0


def test_player_order_insufficient_cash():
    with pytest.raises(ValueError, match="Insufficient cash"):
        # Attempt to buy $50,000 worth of shares (exceeding $30,000 bankroll)
        execute_player_order(action="BUY", ticker="MSFT", shares=1000, force_price=500.0)


def test_player_order_invalid_ticker():
    with pytest.raises(ValueError, match="not part of the 50-stock playing field"):
        execute_player_order(action="BUY", ticker="RANDOM_CO", shares=10, force_price=10.0)


def test_player_order_oversell():
    with pytest.raises(ValueError, match="Cannot sell"):
        execute_player_order(action="SELL", ticker="AAPL", shares=10, force_price=150.0)


def test_bot_evaluate_turn_with_disclosures():
    # Force bot turn
    result = bot_evaluate_turn(force=True, custom_price_map={"NVDA": 200.0, "MU": 120.0, "MSFT": 500.0})
    assert result["status"] == "SUCCESS"

    status = get_live_duel_status(live_prices={})
    assert "player" in status
    assert "bot" in status
    # Bot decisions list is populated if an action was taken
    if status["bot"]["positions"]:
        assert len(status["bot"]["decision_logs"]) > 0
        log = status["bot"]["decision_logs"][0]
        assert "rationale" in log
        assert "ticker" in log


def test_game_initialization():
    state = initialize_game_state(force_reset=True)
    assert state["game_id"] == GAME_ID
    assert state["end_time"] == MATCH_END_ISO
    assert state["initial_capital"] == 30000.0
    assert state["rules"]["min_cash_threshold"] == 3000.0
    assert state["rules"]["quarantine_hours"] == 48
    assert "quarantine" in state["bot"]


def test_quarantine_enforcement():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    quarantine = {}

    # Not quarantined initially
    assert not is_ticker_quarantined("ORCL", quarantine, current_time=now)

    # Add to quarantine
    add_ticker_to_quarantine("ORCL", quarantine, current_time=now, hours=48)
    assert is_ticker_quarantined("ORCL", quarantine, current_time=now)
    assert is_ticker_quarantined("ORCL", quarantine, current_time=now + timedelta(hours=24))

    # After 49 hours, expired
    assert not is_ticker_quarantined("ORCL", quarantine, current_time=now + timedelta(hours=49))


def test_scraps_rule_preservation(tmp_path, monkeypatch):
    test_game_file = str(tmp_path / "scraps_game.json")
    monkeypatch.setenv("WAVE_RIDER_GAME_FILE", test_game_file)
    state = initialize_game_state(force_reset=True)

    # Set bot cash below $3,000 threshold
    state["bot"]["cash"] = 2500.0
    from src.game.duel import save_game_state
    save_game_state(state)

    res = bot_evaluate_turn(force=True, custom_price_map={"NVDA": 200.0})
    # Should not take any buy actions
    assert res["actions_count"] == 0
    updated_state = initialize_game_state()
    assert updated_state["bot"]["cash"] == 2500.0  # Cash perfectly preserved


def test_macro_regime_gatekeeper():
    # Test gatekeeper with mock/fallback
    regime = is_macro_regime_bullish("QQQ")
    assert isinstance(regime, bool)


def test_conviction_weighted_sizing():
    # Tier 1 Sniper: Score >= 90 & RVOL >= 2.0 -> 0.50
    tier1 = {"composite_score": 95, "rvol": 2.5, "smart_money": {"politician_buy": True}}
    assert calculate_conviction_allocation(tier1, available_cash=30000.0) == 0.50

    # Tier 2 Standard: Score 80 - 89 -> 0.25
    tier2 = {"composite_score": 85, "rvol": 1.5, "smart_money": {}}
    assert calculate_conviction_allocation(tier2, available_cash=30000.0) == 0.25

    # Tier 3 Sub-threshold: Score < 80 -> 0.0
    tier3 = {"composite_score": 75, "rvol": 1.2, "smart_money": {}}
    assert calculate_conviction_allocation(tier3, available_cash=30000.0) == 0.0


