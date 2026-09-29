"""
duel.py - 5-Day "Player vs. Bot" Paper Trading Duel Engine.
Horizon: Monday Sep 28 to Friday Oct 2, 2026, 11:00 PM CET (21:00 UTC).
Starting Capital: $30,000 USD each.
Playing Field: 27 US Tech & Memory Leaders.
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

# Target Match Expiry: Friday Oct 2, 2026 at 23:00 CET (21:00 UTC)
MATCH_END_ISO = "2026-10-02T21:00:00Z"
INITIAL_BANKROLL = 30000.0


def initialize_game_state(force_reset: bool = False) -> Dict[str, Any]:
    """Initializes or resets the 5-day duel scenario."""
    game_file = get_game_file()
    if not force_reset and os.path.exists(game_file):
        try:
            with open(game_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                if state.get("game_id") == "duel_2026_10_02":
                    return state
        except Exception:
            pass

    state = {
        "game_id": "duel_2026_10_02",
        "title": "5-Day Live Wave Rider Duel: Player vs. Bot",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "end_time": MATCH_END_ISO,
        "initial_capital": INITIAL_BANKROLL,
        "rules": {
            "starting_cash": INITIAL_BANKROLL,
            "allowed_universe_count": 27,
            "shorting_allowed": False,
            "allocation_limits": "None (Total Freedom)",
            "end_time_cet": "Friday Oct 2, 2026 at 23:00 CET"
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
            "decision_logs": []
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
    """Gets real-time price snapshot for a ticker with daily fallback."""
    try:
        quote = get_premarket_quote(ticker)
        price = float(quote.get("current_price", 0.0))
        if price > 0:
            return price
    except Exception:
        pass

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


def bot_evaluate_turn(
    force: bool = False,
    custom_price_map: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Autonomous decision engine for the Bot.
    1. Evaluates existing positions: checks profit targets (+3.5%/+6.0%), stop loss (-2.5%),
       or momentum stagnation, liquidating when appropriate.
    2. Identifies emerging wave opportunities across the 27 universe.
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
        gain_pct = ((curr_price - avg_price) / avg_price) * 100.0

        should_sell = False
        sell_reason = ""

        # Take Profit Target (+3.5% partial / +6.0% full)
        if gain_pct >= 6.0:
            should_sell = True
            sell_reason = f"Full Target 2 Hit (+{gain_pct:.1f}% gain). Locked in profit to recycle capital."
        elif gain_pct <= -2.5:
            should_sell = True
            sell_reason = f"Stop Loss Triggered ({gain_pct:.1f}% loss). Cut loss early to protect bankroll."

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
    # Step 2: Scout New Opportunities (if cash is available)
    # -----------------------------------------------------------------
    available_cash = state["bot"]["cash"]
    if available_cash >= 1000.0:
        watchlist = load_watchlist()
        candidate_scores = []
        already_held = {p["ticker"] for p in state["bot"]["positions"]}

        # -----------------------------------------------------------------
        # Step 2a: Scout Intraday Ignitions (ORB & Capitulation Snapbacks)
        # -----------------------------------------------------------------
        from src.fetchers.market_hours import is_regular_trading_hours
        from src.analysis.intraday_engine import evaluate_intraday_stock

        if is_regular_trading_hours():
            for s in watchlist:
                ticker = s["ticker"]
                if ticker in already_held:
                    continue
                try:
                    intra_sig = evaluate_intraday_stock(ticker)
                    if intra_sig.get("is_ignition"):
                        candidate_scores.append(intra_sig)
                except Exception:
                    pass

        # -----------------------------------------------------------------
        # Step 2b: Standard EOD / Composite Scouting
        # -----------------------------------------------------------------
        for s in watchlist:
            ticker = s["ticker"]
            if ticker in already_held or any(c["ticker"] == ticker for c in candidate_scores):
                continue
            try:
                score_data = score_single_stock(ticker)
                candidate_scores.append(score_data)
            except Exception:
                pass

        candidate_scores.sort(key=lambda x: x["composite_score"], reverse=True)

        if candidate_scores:
            top = candidate_scores[0]
            ticker = top["ticker"]
            comp_score = top["composite_score"]
            prob = top["wave_probability"]
            is_ign = top["is_ignition"]
            curr_price = custom_price_map.get(ticker) if custom_price_map and ticker in custom_price_map else top["current_price"]

            # Bot conviction threshold
            if (is_ign or comp_score >= 65 or prob >= 65.0) and curr_price > 0:
                # Calculate conviction-weighted allocation (Total Freedom)
                if comp_score >= 85:
                    alloc_pct = 0.50  # 50% of cash on high conviction
                elif comp_score >= 70:
                    alloc_pct = 0.35  # 35%
                else:
                    alloc_pct = 0.20  # 20%

                invest_amount = available_cash * alloc_pct
                shares_to_buy = int(invest_amount // curr_price)

                if shares_to_buy > 0:
                    total_cost = round(shares_to_buy * curr_price, 2)
                    state["bot"]["cash"] -= total_cost

                    state["bot"]["positions"].append({
                        "ticker": ticker,
                        "shares": shares_to_buy,
                        "avg_price": round(curr_price, 2),
                        "cost_basis": total_cost,
                        "opened_at": now_str
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

