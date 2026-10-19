"""
test_week3_rules.py - Comprehensive Unit & Verification Suite for Week 3 Duel Rules:
  1. Multi-Tranche Partial Scaling (50% Harvest at +3.0%)
  2. Dynamic High-Water Mark Profit Ratchet
  3. Breakeven Runner Armor (SPCX Rule)
  4. Portfolio Risk Concentration: Max 4 Concurrent Positions Cap
  5. Correlated Sector Exposure: Max 2 Holdings per Sector
  6. 48-Hour Momentum Stagnation Capital Recycling
  7. Macro Sector Taxonomy Integrity (50/50 Coverage)
"""

import os
import json
import pytest
from datetime import datetime, timezone, timedelta

from src.game.duel import (
    initialize_game_state,
    save_game_state,
    get_live_duel_status,
    bot_evaluate_turn,
    get_ticker_sector,
    compute_dynamic_trailing_stop,
    SECTOR_MAP,
    MAX_ACTIVE_POSITIONS,
    MAX_SECTOR_POSITIONS,
    TARGET_1_HARVEST_PCT,
    TARGET_2_FULL_PCT,
    INITIAL_BANKROLL
)
from src.fetchers.price_fetcher import load_watchlist


@pytest.fixture(autouse=True)
def reset_test_duel(tmp_path, monkeypatch):
    """Isolates game state file for every individual test and mocks slow network scoring."""
    test_file = str(tmp_path / "test_game_week3.json")
    monkeypatch.setenv("WAVE_RIDER_GAME_FILE", test_file)
    monkeypatch.setattr("src.game.duel.is_macro_regime_bullish", lambda *args, **kwargs: True)
    # Default mock: sub-threshold (score 50), so Step 2 won't buy unless a test explicitly provides candidates
    monkeypatch.setattr(
        "src.game.duel.score_single_stock",
        lambda ticker: {
            "ticker": ticker,
            "composite_score": 50,
            "wave_probability": 40.0,
            "is_ignition": False,
            "current_price": 100.0,
            "smart_money": {}
        }
    )
    initialize_game_state(force_reset=True)
    yield


def test_sector_taxonomy_covers_entire_50_universe():
    """Validates that all 50 stocks in watchlist.json map to the 4 approved macro sectors."""
    watchlist = load_watchlist()
    assert len(watchlist) == 50, f"Expected 50 stocks, found {len(watchlist)}"
    
    valid_sectors = {
        "SEMICONDUCTORS",
        "AI_COMPUTE_SYSTEMS",
        "CLOUD_SOFTWARE",
        "MEGACAP_INFRASTRUCTURE"
    }

    for stock in watchlist:
        ticker = stock["ticker"]
        sector = get_ticker_sector(ticker)
        assert sector in valid_sectors, f"Ticker {ticker} mapped to invalid sector: {sector}"
        assert ticker in SECTOR_MAP, f"Ticker {ticker} missing from SECTOR_MAP lookup"


def test_dynamic_trailing_ratchet_floors():
    """Tests that trailing stops ratchet upwards with high-water marks and never drop."""
    pos = {
        "ticker": "SPCX",
        "shares": 30,
        "avg_price": 100.0,
        "cost_basis": 3000.0,
        "peak_price": 100.0,
        "trailing_stop": 97.50,
        "partial_harvested": False
    }

    # At Entry (0.0% gain): stop at -2.5% ($97.50)
    stop = compute_dynamic_trailing_stop(pos, curr_price=100.0)
    assert stop == 97.50

    # At +2.6% peak: stop ratchets to Breakeven ($100.00)
    pos["peak_price"] = 102.60
    stop = compute_dynamic_trailing_stop(pos, curr_price=102.60)
    assert stop == 100.00
    pos["trailing_stop"] = stop

    # At +3.6% peak: stop ratchets to Entry + 1.5% ($101.50)
    pos["peak_price"] = 103.60
    stop = compute_dynamic_trailing_stop(pos, curr_price=103.60)
    assert stop == 101.50
    pos["trailing_stop"] = stop

    # At +4.5% peak: stop ratchets to Entry + 2.5% ($102.50)
    pos["peak_price"] = 104.50
    stop = compute_dynamic_trailing_stop(pos, curr_price=104.50)
    assert stop == 102.50
    pos["trailing_stop"] = stop

    # Price pulls back to $102.80: stop remains locked at $102.50 (Never decreases!)
    stop_pullback = compute_dynamic_trailing_stop(pos, curr_price=102.80)
    assert stop_pullback == 102.50


def test_target_1_partial_harvest():
    """Verifies that at +3.0% gain, 50% shares sell, proceeds go to cash, and stop becomes breakeven."""
    state = initialize_game_state()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Bot holds 20 shares of NVDA @ $100.00 (Cost Basis: $2,000)
    state["bot"]["positions"] = [{
        "ticker": "NVDA",
        "shares": 20,
        "avg_price": 100.0,
        "cost_basis": 2000.0,
        "opened_at": now_str,
        "peak_price": 100.0,
        "trailing_stop": 97.5,
        "partial_harvested": False,
        "sector": "AI_COMPUTE_SYSTEMS"
    }]
    state["bot"]["cash"] = 28000.0
    save_game_state(state)

    # Price rises to $103.50 (+3.5% gain)
    result = bot_evaluate_turn(force=True, custom_price_map={"NVDA": 103.50}, skip_scouting=True)
    assert result["status"] == "SUCCESS"

    updated_state = initialize_game_state()
    # 50% harvested: 10 shares remain
    assert len(updated_state["bot"]["positions"]) == 1
    rem_pos = updated_state["bot"]["positions"][0]
    assert rem_pos["shares"] == 10
    assert rem_pos["partial_harvested"] is True
    # Trailing stop on runner elevated to at least Breakeven ($100.00)
    assert rem_pos["trailing_stop"] >= 100.0

    # Realized proceeds = 10 sh * $103.50 = $1,035.00 cash added
    assert updated_state["bot"]["cash"] == 28000.0 + 1035.00

    # History logs SELL (PARTIAL)
    last_tx = updated_state["bot"]["history"][-1]
    assert last_tx["action"] == "SELL (PARTIAL)"
    assert last_tx["shares"] == 10
    assert last_tx["realized_pnl"] == 35.00


def test_profit_ratchet_exit_prevents_spcx_roundtrip():
    """
    Forensic Simulation of the SPCX Week 2 flaw:
    Surging to +4.45% then pulling back MUST exit with locked profit, not a loss.
    """
    state = initialize_game_state()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Bot holds 30 shares of SPCX @ $100.00
    state["bot"]["positions"] = [{
        "ticker": "SPCX",
        "shares": 30,
        "avg_price": 100.0,
        "cost_basis": 3000.0,
        "opened_at": now_str,
        "peak_price": 100.0,
        "trailing_stop": 97.5,
        "partial_harvested": False,
        "sector": "MEGACAP_INFRASTRUCTURE"
    }]
    state["bot"]["cash"] = 27000.0
    save_game_state(state)

    # 1. Tuesday: SPCX hits $104.45 (+4.45% peak) -> Partial Harvest occurs
    bot_evaluate_turn(force=True, custom_price_map={"SPCX": 104.45}, skip_scouting=True)
    
    mid_state = initialize_game_state()
    assert len(mid_state["bot"]["positions"]) == 1
    pos = mid_state["bot"]["positions"][0]
    assert pos["shares"] == 15
    assert pos["partial_harvested"] is True
    # Peak price updated to $104.45, so trailing stop ratcheted to at least $101.50 (+1.5%)
    assert pos["trailing_stop"] >= 101.50

    # 2. Thursday: Pullback drops price to $101.00 (below ratcheted floor)
    bot_evaluate_turn(force=True, custom_price_map={"SPCX": 101.00}, skip_scouting=True)

    final_state = initialize_game_state()
    # Entire position exited cleanly before crash!
    assert len(final_state["bot"]["positions"]) == 0
    # Net cash is strictly greater than initial bankroll: trade was NET PROFITABLE!
    assert final_state["bot"]["cash"] > 30000.0


def test_max_four_positions_cap():
    """Verifies that the bot refuses to open a 5th position when 4 holdings are active."""
    state = initialize_game_state()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Bot holds 4 positions across 4 sectors at flat market price
    state["bot"]["positions"] = [
        {"ticker": "NVDA", "shares": 10, "avg_price": 100.0, "cost_basis": 1000.0, "opened_at": now_str, "trailing_stop": 97.5, "sector": "AI_COMPUTE_SYSTEMS"},
        {"ticker": "SNOW", "shares": 10, "avg_price": 100.0, "cost_basis": 1000.0, "opened_at": now_str, "trailing_stop": 97.5, "sector": "CLOUD_SOFTWARE"},
        {"ticker": "MSFT", "shares": 5, "avg_price": 100.0, "cost_basis": 500.0, "opened_at": now_str, "trailing_stop": 97.5, "sector": "MEGACAP_INFRASTRUCTURE"},
        {"ticker": "MU", "shares": 20, "avg_price": 100.0, "cost_basis": 2000.0, "opened_at": now_str, "trailing_stop": 97.5, "sector": "SEMICONDUCTORS"},
    ]
    state["bot"]["cash"] = 25500.0  # Plenty of cash available
    save_game_state(state)

    # Trigger evaluation with flat prices (0% change, no stops or targets triggered)
    flat_prices = {"NVDA": 100.0, "SNOW": 100.0, "MSFT": 100.0, "MU": 100.0}
    res = bot_evaluate_turn(force=True, custom_price_map=flat_prices)
    assert res["status"] == "SUCCESS"

    after_state = initialize_game_state()
    # Still exactly 4 positions! No 5th position opened
    assert len(after_state["bot"]["positions"]) == 4

    # Decision log confirms CAPACITY_HOLD
    logs = after_state["bot"]["decision_logs"]
    assert any(log.get("action") == "CAPACITY_HOLD" for log in logs)


def test_max_two_sector_positions_cap(monkeypatch):
    """Verifies that when 2 positions in a sector are already held, candidates from that sector are skipped."""
    state = initialize_game_state()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Bot already holds 2 Semiconductor stocks (MU and LRCX) at flat prices
    state["bot"]["positions"] = [
        {"ticker": "MU", "shares": 20, "avg_price": 100.0, "cost_basis": 2000.0, "opened_at": now_str, "trailing_stop": 97.5, "sector": "SEMICONDUCTORS"},
        {"ticker": "LRCX", "shares": 5, "avg_price": 100.0, "cost_basis": 500.0, "opened_at": now_str, "trailing_stop": 97.5, "sector": "SEMICONDUCTORS"},
    ]
    state["bot"]["cash"] = 27500.0
    save_game_state(state)

    # Monkeypatch candidate scoring:
    # KLAC (Semis) has highest score (92), but sector is full (2/2)
    # SNOW (Cloud) has score 85 (eligible)
    def mock_scores(ticker):
        if ticker == "KLAC":
            return {"ticker": "KLAC", "composite_score": 92, "wave_probability": 80.0, "is_ignition": True, "current_price": 100.0, "smart_money": {}}
        elif ticker == "SNOW":
            return {"ticker": "SNOW", "composite_score": 85, "wave_probability": 70.0, "is_ignition": True, "current_price": 100.0, "smart_money": {}}
        return {"ticker": ticker, "composite_score": 50, "wave_probability": 30.0, "is_ignition": False, "current_price": 100.0, "smart_money": {}}

    monkeypatch.setattr("src.game.duel.score_single_stock", mock_scores)

    # Bot evaluates turn with flat prices
    bot_evaluate_turn(force=True, custom_price_map={"MU": 100.0, "LRCX": 100.0, "KLAC": 100.0, "SNOW": 100.0})

    after_state = initialize_game_state()
    # KLAC must have been skipped because Semis is capped at 2!
    # SNOW must have been bought!
    assert any(p["ticker"] == "SNOW" for p in after_state["bot"]["positions"])
    assert not any(p["ticker"] == "KLAC" for p in after_state["bot"]["positions"])
    
    semis_count = sum(1 for p in after_state["bot"]["positions"] if get_ticker_sector(p["ticker"]) == "SEMICONDUCTORS")
    assert semis_count == 2, f"Expected 2 semiconductors, found {semis_count}"


def test_stagnation_exit_after_48_hours():
    """Verifies that a position held for >= 48 hours without making a new high is liquidated."""
    state = initialize_game_state()
    
    # Position opened 50 hours ago
    old_time = (datetime.now(timezone.utc) - timedelta(hours=50)).strftime("%Y-%m-%d %H:%M UTC")
    state["bot"]["positions"] = [{
        "ticker": "AAPL",
        "shares": 15,
        "avg_price": 200.0,
        "cost_basis": 3000.0,
        "opened_at": old_time,
        "peak_price": 205.0,  # Peaked earlier at +2.5%
        "trailing_stop": 195.0,
        "partial_harvested": False,
        "sector": "MEGACAP_INFRASTRUCTURE"
    }]
    state["bot"]["cash"] = 27000.0
    save_game_state(state)

    # Current price is $203.60 (+1.8% green, but below $205 peak after 50h)
    bot_evaluate_turn(force=True, custom_price_map={"AAPL": 203.60}, skip_scouting=True)

    after_state = initialize_game_state()
    # Position harvested and closed to recycle capital
    assert len(after_state["bot"]["positions"]) == 0
    assert after_state["bot"]["cash"] == 27000.0 + (15 * 203.60)
    
    last_disc = after_state["bot"]["decision_logs"][-1]
    assert "48-Hour Momentum Stagnation Harvest" in last_disc["rationale"]
