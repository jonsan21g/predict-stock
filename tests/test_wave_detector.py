import pytest
import pandas as pd
from src.analysis.wave_detector import detect_wave_ignition


def test_wave_ignition_valid():
    bar = pd.Series({
        "Close": 100.0,
        "Open": 95.0,
        "High": 101.0,
        "Low": 94.0,
        "rvol_20d": 2.2,
        "crr": 0.85,
        "EMA5": 98.0,
        "EMA20": 94.0,
        "ema20_spread": 0.063,
        "is_20d_high_breakout": 1,
        "bb_breakout": 1,
        "bb_squeeze": 0
    })

    result = detect_wave_ignition(bar, pd.DataFrame())
    assert result["is_ignition"] is True
    assert result["entry_price"] == 100.0
    assert result["target_1"] == 103.5
    assert result["target_2"] == 106.0
    assert result["stop_loss"] == 97.5
    assert result["max_holding_days"] == 5


def test_wave_ignition_rejection_low_volume():
    bar = pd.Series({
        "Close": 100.0,
        "Open": 95.0,
        "High": 101.0,
        "Low": 94.0,
        "rvol_20d": 0.8,
        "crr": 0.85,
        "EMA5": 98.0,
        "EMA20": 94.0,
        "ema20_spread": 0.063,
        "is_20d_high_breakout": 1,
        "bb_breakout": 0,
        "bb_squeeze": 0
    })

    result = detect_wave_ignition(bar, pd.DataFrame())
    assert result["is_ignition"] is False


def test_wave_ignition_rejection_extended():
    bar = pd.Series({
        "Close": 115.0,
        "Open": 110.0,
        "High": 116.0,
        "Low": 109.0,
        "rvol_20d": 2.5,
        "crr": 0.85,
        "EMA5": 110.0,
        "EMA20": 100.0,
        "ema20_spread": 0.15,
        "is_20d_high_breakout": 1,
        "bb_breakout": 1,
        "bb_squeeze": 0
    })

    result = detect_wave_ignition(bar, pd.DataFrame())
    assert result["is_ignition"] is False
