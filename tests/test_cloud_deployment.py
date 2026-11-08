"""
test_cloud_deployment.py - Unit & Verification Suite for Static Cloud Bundle Exporter
and Capitulation Reversal Carve-Out Execution:
  1. Static Cloud Exporter Fast Bundle Compilation (TC-DEP-01)
  2. CLI --export-static Execution (TC-DEP-02)
  3. Macro Capitulation Carve-Out Execution (TC-CARVE-01)
  4. Macro Capitulation Rejection on Unconfirmed Traps (TC-CARVE-02)
"""

import os
import sys
import json
import subprocess
import pytest
import pandas as pd
from datetime import datetime, timezone

from src.cloud.static_exporter import export_cloud_bundle
from src.game.duel import (
    initialize_game_state,
    bot_evaluate_turn,
    scout_capitulation_carveout,
    get_live_duel_status
)


@pytest.fixture(autouse=True)
def isolate_game_state(tmp_path, monkeypatch):
    """Isolates the duel game state file for every test."""
    test_file = str(tmp_path / "test_cloud_game.json")
    monkeypatch.setenv("WAVE_RIDER_GAME_FILE", test_file)
    initialize_game_state(force_reset=True)
    yield


def test_static_exporter_fast_bundle(tmp_path, monkeypatch):
    """TC-DEP-01: Verifies that export_cloud_bundle compiles all static SPA assets and core JSON APIs."""
    out_dir = str(tmp_path / "test_dist")

    # Mock heavy network scanners to keep test fast (<2s)
    monkeypatch.setattr("src.cloud.static_exporter.scan_and_rank_watchlist", lambda: [
        {"ticker": "NVDA", "composite_score": 95, "current_price": 120.0, "is_ignition": True, "wave_probability": 85.0}
    ])
    monkeypatch.setattr("src.cloud.static_exporter.scan_intraday_watchlist", lambda: [
        {"ticker": "TSLA", "composite_score": 88, "current_price": 350.0, "is_ignition": True}
    ])

    summary = export_cloud_bundle(output_dir=out_dir, mode="fast", max_tickers=1)

    assert summary["status"] == "SUCCESS"
    assert summary["files_exported"] >= 6

    # 1. HTML index check
    html_path = os.path.join(out_dir, "index.html")
    assert os.path.exists(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "./static/style.css" in html
    assert "./static/app.js" in html

    # 2. Static CSS/JS
    assert os.path.exists(os.path.join(out_dir, "static", "style.css"))
    assert os.path.exists(os.path.join(out_dir, "static", "app.js"))

    # 3. Health API
    health_path = os.path.join(out_dir, "api", "health.json")
    assert os.path.exists(health_path)
    with open(health_path, "r", encoding="utf-8") as f:
        health = json.load(f)
    assert health["status"] == "UP"
    assert health["mode"] == "STATIC_CLOUD_BUNDLE"

    # 4. Game API
    game_path = os.path.join(out_dir, "api", "game.json")
    assert os.path.exists(game_path)
    with open(game_path, "r", encoding="utf-8") as f:
        game = json.load(f)
    assert "player" in game and "bot" in game
    assert game["bot_auto_active"] is True

    # 5. Radar APIs
    for m in ["eod", "premarket", "intraday"]:
        rp = os.path.join(out_dir, "api", f"radar_{m}.json")
        assert os.path.exists(rp)
        with open(rp, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)


def test_cli_export_static_flag(tmp_path):
    """TC-DEP-02: Verifies that python -m src.main --export-static executes successfully via CLI."""
    out_dir = str(tmp_path / "cli_dist")
    api_dir = os.path.join(out_dir, "api")
    os.makedirs(api_dir, exist_ok=True)
    # Pre-seed radar_eod.json so CLI fast export reuses it
    with open(os.path.join(api_dir, "radar_eod.json"), "w", encoding="utf-8") as f:
        json.dump([{"ticker": "NVDA", "composite_score": 90, "current_price": 120.0}], f)

    cmd = [
        sys.executable,
        "-m",
        "src.main",
        "--export-static",
        "--export-mode",
        "fast",
        "--export-dir",
        out_dir
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"CLI export failed with code {res.returncode}: {res.stderr}"
    assert "Export finished successfully" in res.stdout
    assert os.path.exists(os.path.join(out_dir, "index.html"))
    assert os.path.exists(os.path.join(out_dir, "api", "health.json"))


def test_capitulation_carveout_execution(monkeypatch):
    """TC-CARVE-01: Verifies that Bot triggers a tactical capitulation carve-out during macro downtrend when confirmed."""
    # Force QQQ into macro bear regime (QQQ < 20 EMA)
    monkeypatch.setattr("src.game.duel.is_macro_regime_bullish", lambda ticker="QQQ": False)

    # Mock watchlist to a single candidate
    mock_watchlist = [{"ticker": "TSLA", "name": "Tesla, Inc.", "category": "Mega-Cap Anchors"}]
    monkeypatch.setattr("src.game.duel.load_watchlist", lambda: mock_watchlist)

    # Construct mock daily history: Day T-1 crashed -9.5%, Day T confirmed green (Close > Open and Close > Prior Close)
    dates = pd.date_range("2026-10-01", periods=10, freq="D")
    df_mock = pd.DataFrame({
        "Open":   [380.0, 382.0, 385.0, 384.0, 386.0, 388.0, 390.0, 392.0, 390.0, 350.0],
        "High":   [385.0, 386.0, 388.0, 387.0, 389.0, 392.0, 394.0, 395.0, 392.0, 362.0],
        "Low":    [378.0, 380.0, 382.0, 380.0, 383.0, 385.0, 387.0, 389.0, 345.0, 348.0],
        "Close":  [382.0, 384.0, 386.0, 385.0, 388.0, 390.0, 392.0, 391.0, 354.0, 360.0], # Day T-1: 391 -> 354 (-9.46%); Day T: Open 350, Close 360 (+2.8% green)
        "Volume": [1000000] * 10
    }, index=dates)

    history_map = {"TSLA": df_mock}

    # 1. Direct scout check
    candidate = scout_capitulation_carveout(
        watchlist=mock_watchlist,
        already_held=set(),
        bot_quarantine={},
        custom_history_map=history_map
    )
    assert candidate is not None
    assert candidate["ticker"] == "TSLA"
    assert candidate["prior_drop_pct"] <= -8.0
    assert candidate["structural_stop"] < 360.0

    # 2. Bot turn execution
    res = bot_evaluate_turn(force=True, custom_history_map=history_map)
    assert res["actions_count"] == 1
    assert any("BOUGHT (CARVE-OUT)" in act for act in res["actions_taken"])
    assert any("TSLA" in act for act in res["actions_taken"])

    # Verify game state reflects the carve-out position
    status = get_live_duel_status()
    bot_positions = status["bot"]["positions"]
    assert len(bot_positions) == 1
    pos = bot_positions[0]
    assert pos["ticker"] == "TSLA"
    assert pos["strategy"] == "CAPITULATION_CARVE_OUT"
    assert pos["structural_stop"] == candidate["structural_stop"]
    assert pos["trailing_stop"] == candidate["structural_stop"]
    assert pos["cost_basis"] <= 30000.0 * 0.20 + 100.0 # Capped at 20%


def test_capitulation_rejection_unconfirmed(monkeypatch):
    """TC-CARVE-02: Verifies that Bot refuses to catch an unconfirmed falling knife (Day T Close < Open)."""
    monkeypatch.setattr("src.game.duel.is_macro_regime_bullish", lambda ticker="QQQ": False)
    mock_watchlist = [{"ticker": "TSLA", "name": "Tesla, Inc.", "category": "Mega-Cap Anchors"}]
    monkeypatch.setattr("src.game.duel.load_watchlist", lambda: mock_watchlist)

    # Day T-1 crashed -10%, but Day T continues bleeding (Open 350, Close 342: RED candle)
    dates = pd.date_range("2026-10-01", periods=10, freq="D")
    df_bleeding = pd.DataFrame({
        "Open":   [380.0, 382.0, 385.0, 384.0, 386.0, 388.0, 390.0, 392.0, 390.0, 350.0],
        "High":   [385.0, 386.0, 388.0, 387.0, 389.0, 392.0, 394.0, 395.0, 392.0, 352.0],
        "Low":    [378.0, 380.0, 382.0, 380.0, 383.0, 385.0, 387.0, 389.0, 345.0, 338.0],
        "Close":  [382.0, 384.0, 386.0, 385.0, 388.0, 390.0, 392.0, 391.0, 350.0, 342.0], # Day T is red!
        "Volume": [1000000] * 10
    }, index=dates)

    history_map = {"TSLA": df_bleeding}

    candidate = scout_capitulation_carveout(
        watchlist=mock_watchlist,
        already_held=set(),
        bot_quarantine={},
        custom_history_map=history_map
    )
    assert candidate is None, "Unconfirmed bleeding knife must be rejected"

    res = bot_evaluate_turn(force=True, custom_history_map=history_map)
    # Frozen regime log is recorded, but no buy order/position is initiated
    assert any("MACRO REGIME FROZEN" in act for act in res["actions_taken"])
    assert not any("BOUGHT" in act for act in res["actions_taken"])
    status = get_live_duel_status()
    assert len(status["bot"]["positions"]) == 0
