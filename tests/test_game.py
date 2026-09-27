import os
import pytest
from src.game.duel import (
    initialize_game_state,
    get_live_duel_status,
    execute_player_order,
    bot_evaluate_turn,
    INITIAL_BANKROLL
)


@pytest.fixture(autouse=True)
def reset_game():
    initialize_game_state(force_reset=True)
    yield
    initialize_game_state(force_reset=True)


def test_initial_game_state():
    status = get_live_duel_status(live_prices={})
    assert status["player"]["cash"] == INITIAL_BANKROLL
    assert status["player"]["net_equity"] == INITIAL_BANKROLL
    assert status["bot"]["cash"] == INITIAL_BANKROLL
    assert status["bot"]["net_equity"] == INITIAL_BANKROLL
    assert status["leader"] == "TIED"
    assert "Remaining" in status["countdown"] or "Ends" in status["countdown"]


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
    with pytest.raises(ValueError, match="not part of the 27-stock playing field"):
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

