"""
scheduled_order_runner.py - Market Session Order Execution Daemon.
Queues and automatically executes human player or bot orders at regular US market open or market close.
"""

import sys
import os
import time
import argparse
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.fetchers.market_hours import get_ny_now, is_regular_trading_hours
from src.game.duel import (
    initialize_game_state,
    save_game_state,
    get_current_stock_price,
    execute_player_order
)


def queue_scheduled_order(ticker: str, target_usd: float, action: str = "BUY", participant: str = "PLAYER", condition: str = "MARKET_CLOSE") -> dict:
    """Records the scheduled order in game_state.json for transparency."""
    state = initialize_game_state()
    if "scheduled_orders" not in state:
        state["scheduled_orders"] = []

    target_desc = "16:00:05 EST (22:00:05 CET)" if condition.upper() == "MARKET_CLOSE" else "09:30:05 EST (15:30:05 CET)"
    order_info = {
        "id": f"sched_{len(state['scheduled_orders']) + 1}",
        "participant": participant.upper(),
        "action": action.upper(),
        "ticker": ticker.upper(),
        "target_usd": round(target_usd, 2),
        "condition": condition.upper(),
        "target_time_est": target_desc,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status": "QUEUED"
    }
    # Avoid duplicate active orders with the same condition
    state["scheduled_orders"] = [
        o for o in state["scheduled_orders"]
        if not (o["ticker"] == ticker.upper() and o["action"] == action.upper() and o["condition"] == condition.upper() and o["status"] == "QUEUED")
    ]
    state["scheduled_orders"].append(order_info)
    save_game_state(state)
    return order_info


def wait_and_execute_order(ticker: str, target_usd: float, action: str = "BUY", participant: str = "PLAYER", condition: str = "MARKET_CLOSE"):
    """
    Sleeps until US market open (09:30:05 EST) or market close (16:00:05 EST),
    fetches the market price, calculates the closest whole share count to target_usd, and executes.
    """
    ticker = ticker.upper().strip()
    action = action.upper().strip()
    participant = participant.upper().strip()
    condition = condition.upper().strip()

    is_close = (condition == "MARKET_CLOSE")
    target_hour = 16 if is_close else 9
    target_min = 0 if is_close else 30
    session_label = "Regular Market Close (16:00:05 EST / 22:00:05 CET)" if is_close else "Regular Market Open (09:30:05 EST / 15:30:05 CET)"

    order_info = queue_scheduled_order(ticker=ticker, target_usd=target_usd, action=action, participant=participant, condition=condition)
    print(f"\n=======================================================")
    print(f" [SCHEDULED ORDER QUEUED] {participant} -> {action} {ticker}")
    print(f" Target Capital: ${target_usd:,.2f} USD")
    print(f" Execution Condition: US {session_label}")
    print(f" Order ID: {order_info['id']}")
    print(f"=======================================================\n")

    while True:
        ny_now = get_ny_now()
        target_dt = ny_now.replace(hour=target_hour, minute=target_min, second=5, microsecond=0)
        remaining_sec = (target_dt - ny_now).total_seconds()

        # If already at or past target time today
        if remaining_sec <= 0:
            print(f"\n[TARGET TIME REACHED] Time: {ny_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            break

        hours = int(remaining_sec // 3600)
        minutes = int((remaining_sec % 3600) // 60)
        seconds = int(remaining_sec % 60)
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] Standing by for {condition}... T-minus {hours:02d}h {minutes:02d}m {seconds:02d}s")

        # Sleep up to 30 seconds between checks
        sleep_chunk = min(30.0, max(1.0, remaining_sec))
        time.sleep(sleep_chunk)

    # -------------------------------------------------------------
    # Execute the Market Order
    # -------------------------------------------------------------
    print(f"\n[FETCHING CLOSING MARKET PRICE FOR {ticker}]...")
    # Allow 2-3 seconds for live closing prints to settle
    time.sleep(3)
    live_price = get_current_stock_price(ticker)
    if live_price <= 0:
        print(f"[ERROR] Invalid price {live_price} for {ticker}. Aborting execution.")
        return

    # Calculate whole share count closest to target_usd
    target_shares = round(target_usd / live_price)
    target_shares = max(1, int(target_shares))
    total_cost = round(target_shares * live_price, 2)

    # Validate against available cash
    state = initialize_game_state()
    avail_cash = state["player"]["cash"] if participant == "PLAYER" else state["bot"]["cash"]

    if total_cost > avail_cash:
        target_shares = int(avail_cash // live_price)
        total_cost = round(target_shares * live_price, 2)

    print(f"\n[ORDER EXECUTION SPECIFICATION]")
    print(f"  Ticker:         {ticker}")
    print(f"  Live Price:     ${live_price:.2f}")
    print(f"  Target Capital: ${target_usd:,.2f}")
    print(f"  Closest Shares: {target_shares} sh (${total_cost:,.2f} total, diff: ${abs(total_cost - target_usd):.2f})")
    print(f"  Available Cash: ${avail_cash:,.2f}")

    if target_shares <= 0:
        print(f"[ERROR] Insufficient cash (${avail_cash:.2f}) to purchase even 1 share of {ticker} @ ${live_price:.2f}.")
        return

    try:
        if participant == "PLAYER":
            result = execute_player_order(action=action, ticker=ticker, shares=target_shares, force_price=live_price)
        else:
            raise NotImplementedError("Bot scheduled orders not supported via this runner.")

        print(f"\n=======================================================")
        print(f" [ORDER SUCCESSFULLY FILLED] Transaction ID: {result.get('tx', {}).get('id')}")
        print(f" {action} {target_shares} shares of {ticker} @ ${live_price:.2f} for ${total_cost:,.2f}")
        print(f" Remaining Cash: ${state['player']['cash'] - total_cost:,.2f}")
        print(f"=======================================================\n")

        # Update order status in state
        final_state = initialize_game_state()
        if "scheduled_orders" in final_state:
            for o in final_state["scheduled_orders"]:
                if o["id"] == order_info["id"]:
                    o["status"] = "FILLED"
                    o["filled_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                    o["shares"] = target_shares
                    o["price"] = live_price
                    o["total_usd"] = total_cost
            save_game_state(final_state)

    except Exception as e:
        print(f"[ERROR EXECUTING SCHEDULED ORDER]: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Session Order Execution Daemon")
    parser.add_argument("--ticker", type=str, default="TSLA", help="Stock ticker symbol")
    parser.add_argument("--usd", type=float, default=10000.0, help="Target USD capital amount")
    parser.add_argument("--action", type=str, default="BUY", help="Order action: BUY or SELL")
    parser.add_argument("--participant", type=str, default="PLAYER", help="Participant: PLAYER or BOT")
    parser.add_argument("--condition", type=str, default="MARKET_CLOSE", choices=["MARKET_OPEN", "MARKET_CLOSE"], help="Execution trigger")
    args = parser.parse_args()

    wait_and_execute_order(
        ticker=args.ticker,
        target_usd=args.usd,
        action=args.action,
        participant=args.participant,
        condition=args.condition
    )
