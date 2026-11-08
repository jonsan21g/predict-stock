"""
duel.py - 5-Day "Player vs. Bot" Paper Trading Duel Engine.
Horizon: Monday Sep 28 to Friday Oct 2, 2026, 11:00 PM CET (21:00 UTC).
Starting Capital: $30,000 USD each.
Playing Field: 50 US Tech, Semiconductor, AI & Cloud Titans.
Rules: Long only (no shorting). Market execution. Total allocation freedom.
Bot transparency: Full rationale and outside-the-tool catalyst disclosures logged.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.fetchers.price_fetcher import load_watchlist, get_premarket_quote, get_daily_history
from src.analysis.features import compute_technical_indicators
from src.analysis.wave_classifier import score_single_stock
from src.fetchers.politician_data import get_ticker_congress_signals
from src.fetchers.insider_data import get_insider_signals
from src.fetchers.social_sentiment import get_ticker_social_sentiment

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCHLIST_FILE = os.path.join(BASE_DIR, "data", "watchlist.json")

def get_game_file() -> str:
    return os.environ.get("WAVE_RIDER_GAME_FILE", os.path.join(BASE_DIR, "data", "game_state.json"))

# Target Match Expiry: Friday Nov 13, 2026 at 23:00 CET (22:00 UTC)
MATCH_END_ISO = "2026-11-13T22:00:00Z"
GAME_ID = "duel_2026_11_13"
INITIAL_BANKROLL = 30000.0
MINIMUM_BOT_TRADE_CASH_THRESHOLD = 3000.0  # The Scraps Rule: minimum cash reserve ($3,000 / 10%)
QUARANTINE_HOURS = 48
MAX_ACTIVE_POSITIONS = 4                    # Sniper Focus: Max 4 concurrent holdings
MAX_SECTOR_POSITIONS = 2                    # Correlated Risk Guard: Max 2 positions per sector
TARGET_1_HARVEST_PCT = 3.0                  # Harvest 50% profit at +3.0%
TARGET_2_FULL_PCT = 6.0                     # Full exit on remaining runner at +6.0%
HARD_STOP_LOSS_PCT = -2.5                   # Hard stop floor at -2.5%

# Macro Sector Clusters across the 50 Curated US Equities
SECTOR_MAP = {
    # SEMICONDUCTORS & HARDWARE SILICON (24)
    "MU": "SEMICONDUCTORS", "WDC": "SEMICONDUCTORS", "STX": "SEMICONDUCTORS",
    "SKHY": "SEMICONDUCTORS", "SNDK": "SEMICONDUCTORS", "NTAP": "SEMICONDUCTORS",
    "LRCX": "SEMICONDUCTORS", "AMAT": "SEMICONDUCTORS", "KLAC": "SEMICONDUCTORS",
    "ASML": "SEMICONDUCTORS", "TXN": "SEMICONDUCTORS", "SNPS": "SEMICONDUCTORS",
    "CDNS": "SEMICONDUCTORS", "TER": "SEMICONDUCTORS", "ONTO": "SEMICONDUCTORS",
    "AVGO": "SEMICONDUCTORS", "QCOM": "SEMICONDUCTORS", "ARM": "SEMICONDUCTORS",
    "MRVL": "SEMICONDUCTORS", "ADI": "SEMICONDUCTORS", "NXPI": "SEMICONDUCTORS",
    "ON": "SEMICONDUCTORS", "TSM": "SEMICONDUCTORS", "INTC": "SEMICONDUCTORS",

    # AI COMPUTE SYSTEMS & PLATFORMS (6)
    "NVDA": "AI_COMPUTE_SYSTEMS", "AMD": "AI_COMPUTE_SYSTEMS", "SMCI": "AI_COMPUTE_SYSTEMS",
    "DELL": "AI_COMPUTE_SYSTEMS", "PLTR": "AI_COMPUTE_SYSTEMS", "CRWV": "AI_COMPUTE_SYSTEMS",

    # CLOUD SOFTWARE & CYBERSECURITY (7)
    "SNOW": "CLOUD_SOFTWARE", "MDB": "CLOUD_SOFTWARE", "NOW": "CLOUD_SOFTWARE",
    "CRM": "CLOUD_SOFTWARE", "PANW": "CLOUD_SOFTWARE", "CRWD": "CLOUD_SOFTWARE",
    "NET": "CLOUD_SOFTWARE",

    # MEGA-CAP ANCHORS & POWER INFRASTRUCTURE (13)
    "MSFT": "MEGACAP_INFRASTRUCTURE", "AAPL": "MEGACAP_INFRASTRUCTURE",
    "GOOGL": "MEGACAP_INFRASTRUCTURE", "AMZN": "MEGACAP_INFRASTRUCTURE",
    "META": "MEGACAP_INFRASTRUCTURE", "TSLA": "MEGACAP_INFRASTRUCTURE",
    "SPCX": "MEGACAP_INFRASTRUCTURE", "ORCL": "MEGACAP_INFRASTRUCTURE",
    "ANET": "MEGACAP_INFRASTRUCTURE", "VRT": "MEGACAP_INFRASTRUCTURE",
    "ETN": "MEGACAP_INFRASTRUCTURE", "ALAB": "MEGACAP_INFRASTRUCTURE",
    "MPWR": "MEGACAP_INFRASTRUCTURE"
}


def get_ticker_sector(ticker: str) -> str:
    """Returns the macro sector cluster for any ticker in the 50 universe."""
    return SECTOR_MAP.get(ticker.upper().strip(), "GENERAL_TECH")


def compute_dynamic_trailing_stop(pos: Dict[str, Any], curr_price: Optional[float] = None) -> float:
    """
    Computes High-Water Mark Profit Ratchet trailing floor:
      - Peak >= +5.5% -> Stop locked at Entry +4.0%
      - Peak >= +4.5% -> Stop locked at Entry +2.5%
      - Peak >= +3.5% -> Stop locked at Entry +1.5%
      - Peak >= +2.5% or Partial Harvested -> Stop locked at Breakeven (0.0% Risk)
      - Default -> Hard stop at Entry -2.5%
    Trailing stop ratchets strictly upwards; never drops.
    """
    avg_price = float(pos.get("avg_price", 0.0))
    if avg_price <= 0:
        return 0.0

    peak_price = float(pos.get("peak_price", avg_price))
    if curr_price is not None:
        peak_price = max(peak_price, curr_price)

    peak_gain_pct = ((peak_price - avg_price) / avg_price) * 100.0
    partial_harvested = bool(pos.get("partial_harvested", False))

    if peak_gain_pct >= 5.5:
        ratchet_stop = avg_price * 1.040  # +4.0%
    elif peak_gain_pct >= 4.5:
        ratchet_stop = avg_price * 1.025  # +2.5%
    elif peak_gain_pct >= 3.5:
        ratchet_stop = avg_price * 1.015  # +1.5%
    elif peak_gain_pct >= 2.5 or partial_harvested:
        ratchet_stop = avg_price * 1.000  # Breakeven
    else:
        structural_stop = float(pos.get("structural_stop", 0.0))
        if structural_stop > 0:
            ratchet_stop = structural_stop
        else:
            ratchet_stop = avg_price * (1.0 + HARD_STOP_LOSS_PCT / 100.0)  # -2.5% Hard Stop

    existing_stop = float(pos.get("trailing_stop", 0.0))
    return round(max(existing_stop, ratchet_stop), 2)


def is_ticker_quarantined(ticker: str, quarantine: Optional[Dict[str, str]], current_time: Optional[datetime] = None) -> bool:
    """Returns True if ticker is currently under 48-hour stop-loss quarantine."""
    if not quarantine or ticker not in quarantine:
        return False
    expiry_str = quarantine.get(ticker)
    if not expiry_str:
        return False
    try:
        exp_dt = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
        now_dt = current_time or datetime.now(timezone.utc)
        return now_dt < exp_dt
    except Exception:
        return False


def add_ticker_to_quarantine(ticker: str, quarantine: Dict[str, str], current_time: Optional[datetime] = None, hours: int = QUARANTINE_HOURS) -> Dict[str, str]:
    """Adds a ticker to the quarantine dictionary with an expiration timestamp."""
    from datetime import timedelta
    now_dt = current_time or datetime.now(timezone.utc)
    exp_dt = now_dt + timedelta(hours=hours)
    quarantine[ticker] = exp_dt.isoformat()
    return quarantine


def is_macro_regime_bullish(custom_benchmark: Optional[str] = "QQQ") -> bool:
    """
    Evaluates whether benchmark equity (QQQ) is trading >= 20-day EMA.
    If False, returns False to prevent opening new long positions in a deteriorating tape.
    """
    try:
        df = get_daily_history(custom_benchmark, period="3mo")
        if df is not None and len(df) >= 20:
            ema20 = float(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
            curr_close = float(df["Close"].iloc[-1])
            return curr_close >= ema20
    except Exception:
        pass
    return True  # Fallback gracefully if benchmark fetch fails


def calculate_conviction_allocation(top_candidate: Dict[str, Any], available_cash: float) -> float:
    """
    Tiered Kelly Allocation:
      - Tier 1 (Sniper): Score >= 90 & RVOL >= 2.0 (or confirmed catalyst) -> 45% - 50%
      - Tier 2 (Standard): Score 80 - 89 -> 20% - 25%
      - Tier 3 (Sub-threshold): Score < 80 -> 0.0 (Do Not Trade)
    """
    score = top_candidate.get("composite_score", 0)
    rvol = top_candidate.get("rvol", 1.0)
    has_catalyst = bool(top_candidate.get("smart_money", {}).get("politician_buy") or 
                        top_candidate.get("smart_money", {}).get("insider_buy") or 
                        top_candidate.get("smart_money", {}).get("contracts", {}).get("has_major_contract"))
    
    if score >= 90 and (rvol >= 2.0 or has_catalyst):
        return 0.50  # 50% Sniper allocation
    elif score >= 80:
        return 0.25  # 25% Standard allocation
    return 0.0      # Reject sub-80 trades


def initialize_game_state(force_reset: bool = False) -> Dict[str, Any]:
    """Initializes or resets the 5-day duel scenario for Week 3."""
    game_file = get_game_file()
    if not force_reset and os.path.exists(game_file):
        try:
            with open(game_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                if state.get("game_id") == GAME_ID:
                    if "quarantine" not in state.get("bot", {}):
                        state["bot"]["quarantine"] = {}
                    return state
                else:
                    # Archive previous week's state safely before initializing Week 3
                    old_game_id = state.get("game_id", "previous_week")
                    archive_dir = os.path.join(BASE_DIR, "data", "history")
                    os.makedirs(archive_dir, exist_ok=True)
                    archive_path = os.path.join(archive_dir, f"game_state_{old_game_id}.json")
                    if not os.path.exists(archive_path):
                        with open(archive_path, "w", encoding="utf-8") as af:
                            json.dump(state, af, indent=2)
        except Exception:
            pass

    state = {
        "game_id": GAME_ID,
        "title": "5-Day Live Wave Rider Duel: Player vs. Bot (Week 6 - Nov 9 to Nov 13, 2026)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "end_time": MATCH_END_ISO,
        "initial_capital": INITIAL_BANKROLL,
        "rules": {
            "starting_cash": INITIAL_BANKROLL,
            "allowed_universe_count": 50,
            "shorting_allowed": False,
            "max_active_positions": MAX_ACTIVE_POSITIONS,
            "max_sector_positions": MAX_SECTOR_POSITIONS,
            "allocation_limits": "Tiered Conviction (45-50% Sniper / 20-25% Standard)",
            "target_1_harvest": f"+{TARGET_1_HARVEST_PCT:.1f}% (Sell 50% & Breakeven Stop on Runner)",
            "target_2_runner": f"+{TARGET_2_FULL_PCT:.1f}% (Full Exit)",
            "hard_stop_loss": f"{HARD_STOP_LOSS_PCT:.1f}%",
            "end_time_cet": "Friday Nov 13, 2026 at 23:00 CET",
            "min_cash_threshold": MINIMUM_BOT_TRADE_CASH_THRESHOLD,
            "quarantine_hours": QUARANTINE_HOURS
        },
        "player": {
            "cash": INITIAL_BANKROLL,
            "positions": [],
            "history": []
        },
        "bot": {
            "cash": INITIAL_BANKROLL,
            "positions": [],
            "history": [],
            "decision_logs": [],
            "quarantine": {}
        }
    }
    save_game_state(state)
    return state


def save_game_state(state: Dict[str, Any]) -> None:
    """Persists game state to data/game_state.json atomically."""
    game_file = get_game_file()
    os.makedirs(os.path.dirname(game_file), exist_ok=True)
    temp_path = game_file + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    if os.path.exists(game_file):
        os.remove(game_file)
    os.rename(temp_path, game_file)


def get_current_stock_price(ticker: str) -> float:
    """Gets real-time price snapshot for a ticker with session awareness and daily fallback."""
    from src.fetchers.market_hours import is_premarket_session
    from src.fetchers.price_fetcher import get_intraday_snapshot, get_premarket_quote

    # 1. If actively in pre-market session (04:00 - 09:30 EST), check pre-market quotes first
    if is_premarket_session():
        try:
            quote = get_premarket_quote(ticker, strict_premarket=True)
            price = float(quote.get("current_price", 0.0))
            if price > 0:
                return price
        except Exception:
            pass

    # 2. For regular hours, after-hours, and overnight/closed, get the latest regular-session snapshot
    try:
        snap = get_intraday_snapshot(ticker)
        price = float(snap.get("current_price", 0.0))
        if price > 0:
            return price
    except Exception:
        pass

    # 3. Fallback to daily history close
    try:
        df = get_daily_history(ticker, period="5d")
        return float(df["Close"].iloc[-1])
    except Exception:
        return 100.0


def calculate_portfolio_valuation(portfolio: Dict[str, Any], live_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Computes mark-to-market net equity and unrealized P&L for a player or bot portfolio."""
    cash = float(portfolio.get("cash", 0.0))
    positions = portfolio.get("positions", [])
    stock_value = 0.0
    updated_positions = []

    for pos in positions:
        ticker = pos["ticker"]
        shares = int(pos["shares"])
        avg_price = float(pos["avg_price"])
        cost_basis = float(pos.get("cost_basis", shares * avg_price))

        curr_price = live_prices.get(ticker) if live_prices and ticker in live_prices else get_current_stock_price(ticker)
        market_val = shares * curr_price
        unrealized_pnl = market_val - cost_basis
        unrealized_pnl_pct = ((curr_price - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0

        stock_value += market_val
        updated_pos = dict(pos)
        updated_pos["current_price"] = round(curr_price, 2)
        updated_pos["market_value"] = round(market_val, 2)
        updated_pos["unrealized_pnl"] = round(unrealized_pnl, 2)
        updated_pos["unrealized_pnl_pct"] = round(unrealized_pnl_pct, 2)

        # Week 3 Dynamic Trailing & Harvest Fields
        peak_val = max(float(pos.get("peak_price", avg_price)), curr_price)
        updated_pos["peak_price"] = round(peak_val, 2)
        updated_pos["peak_gain_pct"] = round(((peak_val - avg_price) / avg_price) * 100.0, 2) if avg_price > 0 else 0.0
        updated_pos["partial_harvested"] = bool(pos.get("partial_harvested", False))
        updated_pos["sector"] = pos.get("sector") or get_ticker_sector(ticker)
        updated_pos["trailing_stop"] = round(compute_dynamic_trailing_stop(pos, curr_price), 2)

        updated_positions.append(updated_pos)

    net_equity = cash + stock_value
    total_pnl = net_equity - INITIAL_BANKROLL
    total_pnl_pct = (total_pnl / INITIAL_BANKROLL) * 100.0

    return {
        "cash": round(cash, 2),
        "stock_value": round(stock_value, 2),
        "net_equity": round(net_equity, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "positions": updated_positions,
        "history": portfolio.get("history", []),
        "decision_logs": portfolio.get("decision_logs", []),
        "last_evaluated_at": portfolio.get("last_evaluated_at", "Awaiting First Check")
    }


def get_live_duel_status(live_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Computes full live match status, leader margin, and remaining countdown clock."""
    state = initialize_game_state()

    player_eval = calculate_portfolio_valuation(state["player"], live_prices)
    bot_eval = calculate_portfolio_valuation(state["bot"], live_prices)

    # Determine leader
    if player_eval["net_equity"] > bot_eval["net_equity"]:
        leader = "PLAYER"
        lead_margin = player_eval["net_equity"] - bot_eval["net_equity"]
        lead_label = f"🏆 Player Leading by +${lead_margin:,.2f}"
    elif bot_eval["net_equity"] > player_eval["net_equity"]:
        leader = "BOT"
        lead_margin = bot_eval["net_equity"] - player_eval["net_equity"]
        lead_label = f"🤖 Bot Leading by +${lead_margin:,.2f}"
    else:
        leader = "TIED"
        lead_margin = 0.0
        lead_label = "⚖️ Tied ($30,000 Starting Line)"

    # Countdown clock calculation
    try:
        end_dt = datetime.fromisoformat(MATCH_END_ISO.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        diff = end_dt - now_dt
        if diff.total_seconds() > 0:
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            countdown_str = f"{days}d {hours}h {minutes}m Remaining"
            is_expired = False
        else:
            countdown_str = "MATCH FINISHED (Final Valuation Locked)"
            is_expired = True
    except Exception:
        countdown_str = "Ends Friday Oct 2 at 23:00 CET"
        is_expired = False

    return {
        "game_id": state["game_id"],
        "title": state["title"],
        "is_expired": is_expired,
        "countdown": countdown_str,
        "leader": leader,
        "lead_margin": round(lead_margin, 2),
        "lead_label": lead_label,
        "player": player_eval,
        "bot": bot_eval
    }


def execute_player_order(
    action: str,
    ticker: str,
    shares: int,
    force_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executes a real-time order for the human player.
    Validates universe, cash availability, and share holdings.
    """
    action = action.upper().strip()
    ticker = ticker.upper().strip()

    if action not in ["BUY", "SELL"]:
        raise ValueError("Invalid order action. Must be 'BUY' or 'SELL'.")

    # Validate ticker in 50 universe
    watchlist = load_watchlist()
    valid_tickers = {s["ticker"] for s in watchlist}
    if ticker not in valid_tickers:
        raise ValueError(f"Ticker {ticker} is not part of the 50-stock playing field.")

    if shares <= 0:
        raise ValueError("Share count must be greater than 0.")

    state = initialize_game_state()
    price = force_price if force_price is not None else get_current_stock_price(ticker)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if action == "BUY":
        total_cost = round(shares * price, 2)
        if state["player"]["cash"] < total_cost:
            raise ValueError(
                f"Insufficient cash! Order requires ${total_cost:,.2f}, but available buying power is ${state['player']['cash']:,.2f}."
            )

        # Deduct cash
        state["player"]["cash"] -= total_cost

        # Update or create position
        positions = state["player"]["positions"]
        existing = next((p for p in positions if p["ticker"] == ticker), None)
        if existing:
            new_shares = existing["shares"] + shares
            new_cost_basis = existing["cost_basis"] + total_cost
            existing["shares"] = new_shares
            existing["cost_basis"] = round(new_cost_basis, 2)
            existing["avg_price"] = round(new_cost_basis / new_shares, 2)
        else:
            positions.append({
                "ticker": ticker,
                "shares": shares,
                "avg_price": round(price, 2),
                "cost_basis": total_cost,
                "opened_at": now_str
            })

        tx = {
            "id": f"tx_p_{len(state['player']['history']) + 1}",
            "time": now_str,
            "participant": "PLAYER",
            "action": "BUY",
            "ticker": ticker,
            "shares": shares,
            "price": round(price, 2),
            "total_usd": total_cost,
            "realized_pnl": 0.0
        }
        state["player"]["history"].append(tx)
        save_game_state(state)
        return {"status": "SUCCESS", "action": "BUY", "ticker": ticker, "shares": shares, "price": price, "tx": tx}

    elif action == "SELL":
        positions = state["player"]["positions"]
        existing = next((p for p in positions if p["ticker"] == ticker), None)
        if not existing or existing["shares"] < shares:
            held = existing["shares"] if existing else 0
            raise ValueError(f"Cannot sell {shares} shares of {ticker}; you only hold {held} shares.")

        proceeds = round(shares * price, 2)
        cost_of_sold_shares = round(shares * existing["avg_price"], 2)
        realized_pnl = round(proceeds - cost_of_sold_shares, 2)

        # Deposit proceeds to cash
        state["player"]["cash"] += proceeds

        # Update position
        existing["shares"] -= shares
        existing["cost_basis"] -= cost_of_sold_shares
        if existing["shares"] <= 0:
            state["player"]["positions"] = [p for p in positions if p["ticker"] != ticker]

        tx = {
            "id": f"tx_p_{len(state['player']['history']) + 1}",
            "time": now_str,
            "participant": "PLAYER",
            "action": "SELL",
            "ticker": ticker,
            "shares": shares,
            "price": round(price, 2),
            "total_usd": proceeds,
            "realized_pnl": realized_pnl
        }
        state["player"]["history"].append(tx)
        save_game_state(state)
        return {"status": "SUCCESS", "action": "SELL", "ticker": ticker, "shares": shares, "price": price, "tx": tx}




def scout_capitulation_carveout(
    watchlist: List[Dict[str, Any]],
    already_held: set,
    bot_quarantine: Dict[str, str],
    custom_history_map: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether any 50-universe stock qualifies for the Capitulation Reversal Carve-Out:
    1. Day T-1 (prior day) suffered extreme crash: return <= -8.0%.
    2. Day T (today) confirmed green: Close > Open and Close > Prior Close.
    3. Returns top candidate with structural stop at Low of Day T-1 (* 0.995).
    """
    candidates = []
    for s in watchlist:
        ticker = s["ticker"]
        if ticker in already_held or is_ticker_quarantined(ticker, bot_quarantine):
            continue
        try:
            if custom_history_map and ticker in custom_history_map:
                df = custom_history_map[ticker]
            else:
                df = get_daily_history(ticker, period="1mo")
            if df is None or len(df) < 3:
                continue

            c_prior = float(df["Close"].iloc[-2])
            c_two_ago = float(df["Close"].iloc[-3])
            prior_ret = (c_prior / c_two_ago) - 1.0

            # Crash condition: <= -8.0%
            if prior_ret <= -0.08:
                c_today = float(df["Close"].iloc[-1])
                o_today = float(df["Open"].iloc[-1])
                low_prior = float(df["Low"].iloc[-2])

                # Green confirmation: Close > Open and Close > Prior Close
                if c_today > o_today and c_today > c_prior:
                    candidates.append({
                        "ticker": ticker,
                        "current_price": c_today,
                        "prior_drop_pct": round(prior_ret * 100.0, 2),
                        "low_prior": low_prior,
                        "structural_stop": round(low_prior * 0.995, 2),
                        "composite_score": 90,
                        "wave_probability": 66.9,
                        "strategy": "CAPITULATION_CARVE_OUT"
                    })
        except Exception:
            pass

    if not candidates:
        return None

    # Pick the deepest capitulation (largest prior drop)
    candidates.sort(key=lambda x: x["prior_drop_pct"])
    return candidates[0]

def bot_evaluate_turn(
    force: bool = False,
    custom_price_map: Optional[Dict[str, float]] = None,
    skip_scouting: bool = False,
    custom_history_map: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Autonomous decision engine for the Bot.
    1. Evaluates existing positions: checks profit targets (+3.5%/+6.0%), stop loss (-2.5%),
       or momentum stagnation, liquidating when appropriate.
    2. Identifies emerging wave opportunities across the 50 universe.
    3. Factors in smart-money footprints, financial news velocity, and external catalysts.
    4. Formulates a fully transparent disclosure thesis and executes.
    """
    state = initialize_game_state()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    actions_taken = []

    # -----------------------------------------------------------------
    # Step 1: Manage Existing Open Positions
    # -----------------------------------------------------------------
    open_bot_positions = list(state["bot"]["positions"])
    for pos in open_bot_positions:
        ticker = pos["ticker"]
        shares = int(pos["shares"])
        avg_price = float(pos["avg_price"])
        curr_price = custom_price_map.get(ticker) if custom_price_map and ticker in custom_price_map else get_current_stock_price(ticker)

        # Track high-water mark peak price
        peak_val = max(float(pos.get("peak_price", avg_price)), curr_price)
        pos["peak_price"] = round(peak_val, 2)
        pos["sector"] = pos.get("sector") or get_ticker_sector(ticker)

        # Update dynamic profit ratchet trailing stop
        dyn_stop = compute_dynamic_trailing_stop(pos, curr_price)
        pos["trailing_stop"] = round(dyn_stop, 2)

        gain_pct = ((curr_price - avg_price) / avg_price) * 100.0
        peak_gain_pct = ((peak_val - avg_price) / avg_price) * 100.0

        from src.fetchers.market_hours import is_regular_trading_hours
        can_execute_orders = is_regular_trading_hours() or force or (custom_price_map is not None)

        # -------------------------------------------------------------
        # Step 1a: Target 1 Partial Profit Scaling (50% Harvest at +3.0%)
        # -------------------------------------------------------------
        if can_execute_orders and gain_pct >= TARGET_1_HARVEST_PCT and not pos.get("partial_harvested", False) and shares >= 2:
            shares_to_sell = shares // 2
            proceeds = round(shares_to_sell * curr_price, 2)
            cost_basis_sold = round(shares_to_sell * avg_price, 2)
            realized_pnl = round(proceeds - cost_basis_sold, 2)

            state["bot"]["cash"] += proceeds
            pos["shares"] -= shares_to_sell
            pos["cost_basis"] = round(pos["shares"] * avg_price, 2)
            pos["partial_harvested"] = True
            # Raise trailing stop on runner to at least Breakeven (0.0% Risk)
            pos["trailing_stop"] = round(max(pos.get("trailing_stop", 0.0), avg_price), 2)

            tx = {
                "id": f"tx_b_{len(state['bot']['history']) + 1}",
                "time": now_str,
                "participant": "BOT",
                "action": "SELL (PARTIAL)",
                "ticker": ticker,
                "shares": shares_to_sell,
                "price": round(curr_price, 2),
                "total_usd": proceeds,
                "realized_pnl": realized_pnl
            }
            state["bot"]["history"].append(tx)

            disclosure = {
                "time": now_str,
                "action": "SELL_PARTIAL",
                "ticker": ticker,
                "shares": shares_to_sell,
                "price": round(curr_price, 2),
                "rationale": (
                    f"Target 1 Harvest (+{gain_pct:.1f}% gain). Sold 50% ({shares_to_sell} sh) to lock profit into bankroll. "
                    f"Trailing stop on remaining {pos['shares']} runner shares elevated to Breakeven (${avg_price:.2f})."
                ),
                "realized_pnl": realized_pnl,
                "pnl_pct": round(gain_pct, 2)
            }
            state["bot"]["decision_logs"].append(disclosure)
            actions_taken.append(f"BOT HARVESTED 50% ({shares_to_sell} sh) {ticker} @ ${curr_price:.2f} (Realized: +${realized_pnl:.2f})")
            shares = pos["shares"]  # Updated share count for subsequent checks

        # -------------------------------------------------------------
        # Step 1b: Full Position Exit Checks (Target 2, Ratchet, Stop, Stagnation)
        # -------------------------------------------------------------
        should_sell = False
        sell_reason = ""

        if can_execute_orders:
            # 1. Full Target 2 Hit (+6.0%)
            if gain_pct >= TARGET_2_FULL_PCT:
                should_sell = True
                sell_reason = f"Full Target 2 Hit (+{gain_pct:.1f}% gain). Locked in profit on remaining runner to recycle capital."

            # 2. Dynamic Trailing Profit Ratchet Exit (Guarantees locked profits before pullback)
            elif curr_price <= pos["trailing_stop"] and pos["trailing_stop"] >= avg_price:
                should_sell = True
                locked_gain = ((curr_price - avg_price) / avg_price) * 100.0
                sell_reason = (
                    f"Dynamic Profit Ratchet Exit triggered @ ${curr_price:.2f} (Floor was ${pos['trailing_stop']:.2f}, "
                    f"peak was ${pos['peak_price']:.2f}). Locked in +{locked_gain:.1f}% gain before pullback."
                )

            # 3. Hard Stop Loss (-2.5%)
            elif gain_pct <= HARD_STOP_LOSS_PCT:
                should_sell = True
                if "quarantine" not in state["bot"]:
                    state["bot"]["quarantine"] = {}
                add_ticker_to_quarantine(ticker, state["bot"]["quarantine"])
                sell_reason = f"Stop Loss Triggered ({gain_pct:.1f}% loss). Cut loss early and quarantined ticker for {QUARANTINE_HOURS} hours."

            # 4. 48-Hour Stagnation Harvest
            elif gain_pct >= 1.5:
                opened_at_str = pos.get("opened_at", "")
                if opened_at_str:
                    try:
                        opened_dt = datetime.strptime(opened_at_str.replace(" UTC", ""), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        now_dt = datetime.now(timezone.utc)
                        hours_held = (now_dt - opened_dt).total_seconds() / 3600.0
                        if hours_held >= 48.0 and curr_price < pos.get("peak_price", curr_price):
                            should_sell = True
                            sell_reason = f"48-Hour Momentum Stagnation Harvest (+{gain_pct:.1f}% gain after {int(hours_held)}h). Recycled capital for fresh Day-1 wave ignition."
                    except Exception:
                        pass

        if should_sell:
            proceeds = round(shares * curr_price, 2)
            cost_basis = round(shares * avg_price, 2)
            realized_pnl = round(proceeds - cost_basis, 2)

            state["bot"]["cash"] += proceeds
            state["bot"]["positions"] = [p for p in state["bot"]["positions"] if p["ticker"] != ticker]

            tx = {
                "id": f"tx_b_{len(state['bot']['history']) + 1}",
                "time": now_str,
                "participant": "BOT",
                "action": "SELL",
                "ticker": ticker,
                "shares": shares,
                "price": round(curr_price, 2),
                "total_usd": proceeds,
                "realized_pnl": realized_pnl
            }
            state["bot"]["history"].append(tx)

            disclosure = {
                "time": now_str,
                "action": "SELL",
                "ticker": ticker,
                "shares": shares,
                "price": round(curr_price, 2),
                "rationale": sell_reason,
                "realized_pnl": realized_pnl,
                "pnl_pct": round(gain_pct, 2)
            }
            state["bot"]["decision_logs"].append(disclosure)
            actions_taken.append(f"BOT SOLD {shares} {ticker} @ ${curr_price:.2f} ({sell_reason})")

    # -----------------------------------------------------------------
    # Step 2: Scout New Opportunities (if portfolio capacity & cash allow)
    # -----------------------------------------------------------------
    if skip_scouting:
        state["bot"]["last_evaluated_at"] = now_str
        save_game_state(state)
        return {
            "status": "SUCCESS",
            "time": now_str,
            "actions_taken": actions_taken,
            "actions_count": len(actions_taken)
        }

    available_cash = state["bot"]["cash"]
    bot_quarantine = state["bot"].get("quarantine", {})

    # Capacity Check 1: Max 4 Active Holdings Cap
    if len(state["bot"]["positions"]) >= MAX_ACTIVE_POSITIONS:
        disclosure = {
            "time": now_str,
            "action": "CAPACITY_HOLD",
            "ticker": "PORTFOLIO",
            "shares": 0,
            "price": 0.0,
            "rationale": f"Max Active Holdings Cap Reached ({len(state['bot']['positions'])}/{MAX_ACTIVE_POSITIONS} positions). Preserving cash reserve to maintain sniper focus.",
            "composite_score": 0,
            "wave_probability": 0.0
        }
        state["bot"]["decision_logs"].append(disclosure)
        actions_taken.append(f"PORTFOLIO FULL: {len(state['bot']['positions'])}/{MAX_ACTIVE_POSITIONS} active holdings (Sniper discipline)")

    # The Scraps Rule: Do not trade if available cash < $3,000 (10% of $30k bankroll)
    elif available_cash >= MINIMUM_BOT_TRADE_CASH_THRESHOLD:
        # Macro Regime Gatekeeper: QQQ >= 20 EMA
        if not is_macro_regime_bullish("QQQ"):
            # Check for Capitulation Reversal Carve-Out (Empirical Edge: PF 1.37, 66.9% Win Rate)
            watchlist = load_watchlist()
            already_held = {p["ticker"] for p in state["bot"]["positions"]}
            has_active_carveout = any(p.get("strategy") == "CAPITULATION_CARVE_OUT" for p in state["bot"]["positions"])

            carveout_candidate = None
            if not has_active_carveout and len(state["bot"]["positions"]) < MAX_ACTIVE_POSITIONS:
                carveout_candidate = scout_capitulation_carveout(
                    watchlist, already_held, bot_quarantine, custom_history_map=custom_history_map
                )

            if carveout_candidate:
                top = carveout_candidate
                ticker = top["ticker"]
                curr_price = custom_price_map.get(ticker) if custom_price_map and ticker in custom_price_map else top["current_price"]
                alloc_pct = 0.20  # 20% Tactical Allocation
                shares_to_buy = int((available_cash * alloc_pct) // curr_price) if curr_price > 0 else 0

                if shares_to_buy > 0:
                    total_cost = round(shares_to_buy * curr_price, 2)
                    state["bot"]["cash"] -= total_cost
                    ticker_sector = get_ticker_sector(ticker)

                    state["bot"]["positions"].append({
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "avg_price": round(curr_price, 2),
                        "cost_basis": total_cost,
                        "opened_at": now_str,
                        "peak_price": round(curr_price, 2),
                        "partial_harvested": False,
                        "trailing_stop": top["structural_stop"],
                        "structural_stop": top["structural_stop"],
                        "sector": ticker_sector,
                        "strategy": "CAPITULATION_CARVE_OUT"
                    })

                    tx = {
                        "id": f"tx_b_{len(state['bot']['history']) + 1}",
                        "time": now_str,
                        "participant": "BOT",
                        "action": "BUY (CAPITULATION CARVE-OUT)",
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "price": round(curr_price, 2),
                        "total_usd": total_cost,
                        "realized_pnl": 0.0
                    }
                    state["bot"]["history"].append(tx)

                    rationale = (
                        f"Capitulation Reversal Carve-Out: Benchmark QQQ < 20 EMA, but {ticker} suffered extreme {top['prior_drop_pct']}% "
                        f"washout on Day T-1 and confirmed green reversal today. Tactical 20% entry (${total_cost:,.2f}) with structural LOD stop "
                        f"at ${top['structural_stop']:.2f}."
                    )
                    disclosure = {
                        "time": now_str,
                        "action": "CAPITULATION_BUY",
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "price": round(curr_price, 2),
                        "total_usd": total_cost,
                        "rationale": rationale,
                        "composite_score": top["composite_score"],
                        "wave_probability": top["wave_probability"]
                    }
                    state["bot"]["decision_logs"].append(disclosure)
                    actions_taken.append(f"BOT BOUGHT (CARVE-OUT) {shares_to_buy} {ticker} @ ${curr_price:.2f} ({rationale})")
            else:
                disclosure = {
                    "time": now_str,
                    "action": "MACRO_HOLD",
                    "ticker": "QQQ",
                    "shares": 0,
                    "price": 0.0,
                    "rationale": "Macro Regime Gatekeeper: Benchmark QQQ is trading below its 20-day EMA. No confirmed capitulation washouts detected. Preserving cash.",
                    "composite_score": 0,
                    "wave_probability": 0.0
                }
                state["bot"]["decision_logs"].append(disclosure)
                actions_taken.append("MACRO REGIME FROZEN: QQQ < 20 EMA (No capitulation washouts confirmed, capital in cash)")
        else:
            watchlist = load_watchlist()
            candidate_scores = []
            already_held = {p["ticker"] for p in state["bot"]["positions"]}

            # Step 2a: Scout Intraday Ignitions (ORB & Capitulation Snapbacks)
            from src.fetchers.market_hours import is_regular_trading_hours
            from src.analysis.intraday_engine import evaluate_intraday_stock

            if is_regular_trading_hours():
                for s in watchlist:
                    ticker = s["ticker"]
                    if ticker in already_held or is_ticker_quarantined(ticker, bot_quarantine):
                        continue
                    try:
                        intra_sig = evaluate_intraday_stock(ticker)
                        if intra_sig.get("is_ignition"):
                            candidate_scores.append(intra_sig)
                    except Exception:
                        pass

            # Step 2b: Standard EOD / Composite Scouting
            for s in watchlist:
                ticker = s["ticker"]
                if ticker in already_held or is_ticker_quarantined(ticker, bot_quarantine) or any(c["ticker"] == ticker for c in candidate_scores):
                    continue
                try:
                    score_data = score_single_stock(ticker)
                    candidate_scores.append(score_data)
                except Exception:
                    pass

            candidate_scores.sort(key=lambda x: x["composite_score"], reverse=True)

            # Filter candidates by Sector Concentration Cap (Max 2 per Sector)
            chosen_candidate = None
            skipped_sector_details = []

            for cand in candidate_scores:
                c_ticker = cand["ticker"]
                c_sector = get_ticker_sector(c_ticker)
                current_sector_count = sum(1 for p in state["bot"]["positions"] if get_ticker_sector(p["ticker"]) == c_sector)
                if current_sector_count >= MAX_SECTOR_POSITIONS:
                    skipped_sector_details.append(f"{c_ticker} ({c_sector} already at {current_sector_count}/{MAX_SECTOR_POSITIONS})")
                    continue
                chosen_candidate = cand
                break

            if chosen_candidate:
                top = chosen_candidate
                ticker = top["ticker"]
                comp_score = top["composite_score"]
                prob = top["wave_probability"]
                is_ign = top["is_ignition"]
                curr_price = custom_price_map.get(ticker) if custom_price_map and ticker in custom_price_map else top["current_price"]

                # Conviction-Weighted Tiered Sizing (Kelly Allocation)
                alloc_pct = calculate_conviction_allocation(top, available_cash)
                shares_to_buy = 0

                if alloc_pct > 0.0 and curr_price > 0:
                    invest_amount = available_cash * alloc_pct
                    shares_to_buy = int(invest_amount // curr_price)

                if shares_to_buy > 0:
                    total_cost = round(shares_to_buy * curr_price, 2)
                    state["bot"]["cash"] -= total_cost

                    ticker_sector = get_ticker_sector(ticker)
                    state["bot"]["positions"].append({
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "avg_price": round(curr_price, 2),
                        "cost_basis": total_cost,
                        "opened_at": now_str,
                        "peak_price": round(curr_price, 2),
                        "partial_harvested": False,
                        "trailing_stop": round(curr_price * (1.0 + HARD_STOP_LOSS_PCT / 100.0), 2),
                        "sector": ticker_sector
                    })

                    tx = {
                        "id": f"tx_b_{len(state['bot']['history']) + 1}",
                        "time": now_str,
                        "participant": "BOT",
                        "action": "BUY",
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "price": round(curr_price, 2),
                        "total_usd": total_cost,
                        "realized_pnl": 0.0
                    }
                    state["bot"]["history"].append(tx)

                    # Gather outside-the-tool context for required transparent disclosure
                    sm = top.get("smart_money", {})
                    if sm.get("jurisdiction_match"):
                        comms = ", ".join(sm.get("matched_committees", []))
                        pol_txt = f"Congressional Committee Oversight BUY ({comms})"
                    elif sm.get("politician_buy"):
                        pol_txt = "Recent Congressional BUY detected"
                    else:
                        pol_txt = "No recent Capitol trades"
                    # Insiders Context
                    if sm.get("insider_cluster"):
                        ins_txt = "Executive Cluster BUY (2+ Insiders)"
                    elif sm.get("c_suite_buyers"):
                        ins_txt = f"C-Suite BUY ({', '.join(sm.get('c_suite_buyers', []))})"
                    elif sm.get("insider_buy"):
                        ins_txt = f"Corporate Insider BUY (${sm.get('total_buy_value_usd', 0):,.0f})"
                    else:
                        ins_txt = "No recent insider buying"

                    # Social & Pelosi Effect Context
                    pe = sm.get("pelosi_effect", {})
                    if pe.get("is_active"):
                        narr = pe.get("narrative_summary", "")
                        sent_txt = f"ACTIVE PELOSI EFFECT [{pe.get('intensity', 'VIRAL')} - {pe.get('primary_catalyst', 'COPYTRADE')}] (Score: {pe.get('hype_score', 0)}/100). {narr}"
                    elif sm.get("viral_politician_buzz"):
                        sent_txt = f"Emerging politician/smart-money social buzz (Score: {sm.get('retail_hype_score', 0)}/100)"
                    else:
                        sent_txt = f"Sentiment is {sm.get('sentiment_label', 'NEUTRAL')}"

                    # Federal Contracts Context
                    fed = sm.get("contracts", {})
                    fed_txt = ""
                    if fed.get("has_major_contract"):
                        val_m = fed.get("total_value_usd", 0.0) / 1_000_000.0
                        agencies = ", ".join(fed.get("top_agencies", []))
                        fed_txt = f", and US Federal Government Contract backing (${val_m:,.0f}M from {agencies})"

                    rationale = (
                        f"Day-1 Wave Ignition: {top.get('ignition_type', 'MOMENTUM_ALIGN')} with RVOL {top.get('rvol', 1.0):.2f}x "
                        f"and P(Wave) of {prob:.1f}%. External catalysts factored: {pol_txt}, {ins_txt}, {sent_txt}{fed_txt}. "
                        f"Allocating ${total_cost:,.2f} ({alloc_pct*100:.0f}% of cash) on high conviction."
                    )

                    disclosure = {
                        "time": now_str,
                        "action": "BUY",
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "price": round(curr_price, 2),
                        "total_usd": total_cost,
                        "rationale": rationale,
                        "composite_score": comp_score,
                        "wave_probability": prob
                    }
                    state["bot"]["decision_logs"].append(disclosure)
                    actions_taken.append(f"BOT BOUGHT {shares_to_buy} {ticker} @ ${curr_price:.2f} ({rationale})")

    state["bot"]["last_evaluated_at"] = now_str
    save_game_state(state)
    return {
        "status": "SUCCESS",
        "time": now_str,
        "actions_taken": actions_taken,
        "actions_count": len(actions_taken)
    }

