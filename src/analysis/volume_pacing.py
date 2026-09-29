"""
volume_pacing.py - Time-of-Day Cumulative Volume Profiling & Pacing Engine.
Models the intraday U-curve volume distribution across regular trading hours (09:30 - 16:00 EST)
to determine whether morning volume velocity represents genuine institutional accumulation.
"""

from datetime import datetime, time
from typing import Optional
from src.fetchers.market_hours import get_ny_now

# Cumulative expected volume fraction by 30-minute intervals across NYSE/NASDAQ equities
# Based on historical median intraday volume curves
TIME_VOLUME_CDF = [
    (time(9, 35), 0.04),   # First 5 mins (~4%)
    (time(9, 45), 0.09),   # First 15 mins (~9%)
    (time(10, 0), 0.15),   # First 30 mins (~15%)
    (time(10, 30), 0.23),  # First 60 mins (~23%)
    (time(11, 0), 0.30),   # 90 mins in (~30%)
    (time(11, 30), 0.36),  # 2 hours in (~36%)
    (time(12, 0), 0.42),   # Midday (~42%)
    (time(13, 0), 0.52),   # Early afternoon (~52%)
    (time(14, 0), 0.62),   # Mid afternoon (~62%)
    (time(15, 0), 0.73),   # Power hour start (~73%)
    (time(15, 30), 0.84),  # Late power hour (~84%)
    (time(16, 0), 1.00)    # Market close (100%)
]


def get_expected_volume_fraction(t: Optional[time] = None) -> float:
    """
    Returns the expected cumulative percentage (0.0 to 1.0) of 20-day average
    daily volume that should have traded by time `t` (US/Eastern).
    """
    if t is None:
        t = get_ny_now().time()

    if t < time(9, 30):
        return 0.02  # Pre-market baseline
    if t >= time(16, 0):
        return 1.00

    # Linear interpolation between reference breakpoints
    prev_time, prev_frac = time(9, 30), 0.01
    for ref_time, ref_frac in TIME_VOLUME_CDF:
        if t <= ref_time:
            # Fraction of progress between prev_time and ref_time
            t_mins = (t.hour * 60 + t.minute) - (prev_time.hour * 60 + prev_time.minute)
            ref_mins = (ref_time.hour * 60 + ref_time.minute) - (prev_time.hour * 60 + prev_time.minute)
            ratio = max(0.0, min(1.0, t_mins / max(1, ref_mins)))
            return prev_frac + ratio * (ref_frac - prev_frac)
        prev_time, prev_frac = ref_time, ref_frac

    return 1.00


def calculate_pacing_rvol(
    cumulative_volume: int,
    vol_sma20: float,
    current_time: Optional[time] = None
) -> float:
    """
    Calculates time-of-day relative volume pacing multiplier.
    Returns: RVOL_pacing (e.g. 1.50 = pacing at 150% of expected institutional rate).
    """
    if vol_sma20 <= 0:
        return 1.0

    exp_frac = get_expected_volume_fraction(current_time)
    expected_vol = vol_sma20 * exp_frac

    if expected_vol <= 0:
        return 1.0

    pacing = cumulative_volume / expected_vol
    return round(float(max(0.10, min(15.0, pacing))), 2)
