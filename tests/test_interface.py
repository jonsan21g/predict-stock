import pytest
from src.dashboard.app import app
from src.main import run_premarket_scan


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"WAVE RIDER" in res.data


def test_dashboard_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "UP"


def test_dashboard_radar_premarket(client):
    res = client.get("/api/radar?mode=premarket")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 27
    assert "ticker" in data[0]
    assert "wave_probability" in data[0]


def test_dashboard_stock_detail(client):
    res = client.get("/api/stock/NVDA")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ticker"] == "NVDA"
    assert "current_price" in data
    assert "composite_score" in data
    assert "history" in data
    assert len(data["history"]) > 0


def test_dashboard_backtest_api(client):
    res = client.get("/api/backtest?ticker=NVDA&period=1y")
    assert res.status_code == 200
    data = res.get_json()
    assert "win_rate_pct" in data
    assert "equity_curve" in data
    assert "trades" in data


def test_cli_premarket_execution():
    # Should execute and format table without raising exception
    run_premarket_scan(top_n=3)


def test_dashboard_game_endpoints(client):
    # 1. Reset game
    res_reset = client.post("/api/game/reset")
    assert res_reset.status_code == 200
    reset_data = res_reset.get_json()
    assert reset_data["status"] == "RESET"

    # 2. Get status
    res_game = client.get("/api/game")
    assert res_game.status_code == 200
    game_data = res_game.get_json()
    assert game_data["player"]["cash"] == 30000.0
    assert game_data["bot"]["cash"] == 30000.0

    # 3. Submit player BUY order
    res_order = client.post("/api/game/order", json={"action": "BUY", "ticker": "NVDA", "shares": 5})
    assert res_order.status_code == 200
    order_data = res_order.get_json()
    assert order_data["status"] == "SUCCESS"
    assert order_data["action"] == "BUY"
    assert order_data["shares"] == 5

    # Verify updated game state
    res_game2 = client.get("/api/game")
    game_data2 = res_game2.get_json()
    assert len(game_data2["player"]["positions"]) == 1
    assert game_data2["player"]["positions"][0]["ticker"] == "NVDA"

    # 4. Trigger bot turn
    res_bot = client.post("/api/game/bot-turn")
    assert res_bot.status_code == 200
    bot_data = res_bot.get_json()
    assert bot_data["status"] == "SUCCESS"

    # 5. Reset again
    res_final_reset = client.post("/api/game/reset")
    assert res_final_reset.status_code == 200



def test_dashboard_game_endpoints(client):
    # 1. Reset game
    res_reset = client.post("/api/game/reset")
    assert res_reset.status_code == 200
    reset_data = res_reset.get_json()
    assert reset_data["status"] == "RESET"

    # 2. Get status
    res_game = client.get("/api/game")
    assert res_game.status_code == 200
    game_data = res_game.get_json()
    assert game_data["player"]["cash"] == 30000.0
    assert game_data["bot"]["cash"] == 30000.0

    # 3. Submit player BUY order
    res_order = client.post("/api/game/order", json={"action": "BUY", "ticker": "NVDA", "shares": 5})
    assert res_order.status_code == 200
    order_data = res_order.get_json()
    assert order_data["status"] == "SUCCESS"
    assert order_data["action"] == "BUY"
    assert order_data["shares"] == 5

    # Verify updated game state
    res_game2 = client.get("/api/game")
    game_data2 = res_game2.get_json()
    assert len(game_data2["player"]["positions"]) == 1
    assert game_data2["player"]["positions"][0]["ticker"] == "NVDA"

    # 4. Trigger bot turn
    res_bot = client.post("/api/game/bot-turn")
    assert res_bot.status_code == 200
    bot_data = res_bot.get_json()
    assert bot_data["status"] == "SUCCESS"

    # 5. Reset again
    res_final_reset = client.post("/api/game/reset")
    assert res_final_reset.status_code == 200


