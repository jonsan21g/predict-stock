"""
market_hours.py - US Eastern Market Session State Machine.
Tracks canonical NYSE/NASDAQ trading sessions:
  - PRE_MARKET: 04:00 - 09:30 EST (Mon-Fri)
  - REGULAR_HOURS: 09:30 - 16:00 EST (Mon-Fri)
  - AFTER_HOURS: 16:00 - 20:00 EST (Mon-Fri)
  - CLOSED: Weekends and 20:00 - 04:00 EST
"""

from enum import Enum
from datetime import datetime, time, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    NY_TZ = ZoneInfo("America/New_York")
except Exception:
    import pytz
    NY_TZ = pytz.timezone("America/New_York")


class MarketSession(str, Enum):
    PRE_MARKET = "PRE_MARKET"
    REGULAR_HOURS = "REGULAR_HOURS"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"


def get_ny_now(dt: Optional[datetime] = None) -> datetime:
    """Returns the current or provided datetime localized to US/Eastern."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(NY_TZ)


def get_current_market_session(dt: Optional[datetime] = None) -> MarketSession:
    """
    Evaluates whether the given timestamp falls into PRE_MARKET, REGULAR_HOURS,
    AFTER_HOURS, or CLOSED (including weekends).
    """
    ny_dt = get_ny_now(dt)

    # Check weekend (5 = Saturday, 6 = Sunday)
    if ny_dt.weekday() in (5, 6):
        return MarketSession.CLOSED

    cur_time = ny_dt.time()

    pre_start = time(4, 0, 0)
    rth_start = time(9, 30, 0)
    rth_end = time(16, 0, 0)
    ah_end = time(20, 0, 0)

    if pre_start <= cur_time < rth_start:
        return MarketSession.PRE_MARKET
    elif rth_start <= cur_time < rth_end:
        return MarketSession.REGULAR_HOURS
    elif rth_end <= cur_time < ah_end:
        return MarketSession.AFTER_HOURS
    else:
        return MarketSession.CLOSED


def is_regular_trading_hours(dt: Optional[datetime] = None) -> bool:
    return get_current_market_session(dt) == MarketSession.REGULAR_HOURS


def is_premarket_session(dt: Optional[datetime] = None) -> bool:
    return get_current_market_session(dt) == MarketSession.PRE_MARKET
