import pytest
import pandas as pd
import numpy as np
from src.analysis.features import (
    compute_technical_indicators,
    create_wave_target,
    build_feature_matrix,
    FEATURE_COLUMNS
)


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range(start="2026-01-01", periods=100, freq="B")
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)
    prices = 100.0 * np.exp(np.cumsum(returns))
    
    highs = prices * (1.0 + np.abs(np.random.normal(0.005, 0.005, 100)))
    lows = prices * (1.0 - np.abs(np.random.normal(0.005, 0.005, 100)))
    opens = (highs + lows) / 2.0
    volumes = np.random.randint(1000000, 5000000, 100)
    
    df = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": prices,
        "Volume": volumes
    }, index=dates)
    return df


def test_compute_technical_indicators(sample_ohlcv):
    enriched = compute_technical_indicators(sample_ohlcv)
    expected_cols = [
        "EMA5", "EMA10", "EMA20", "SMA50", "rvol_20d", "ATR14",
        "crr", "bb_width", "bb_squeeze", "dist_to_20d_high"
    ]
    for col in expected_cols:
        assert col in enriched.columns, f"Missing {col}"
    
    assert (enriched["rvol_20d"].dropna() > 0).all()
    assert ((enriched["crr"] >= 0.0) & (enriched["crr"] <= 1.0)).all()


def test_create_wave_target(sample_ohlcv):
    targets = create_wave_target(sample_ohlcv, target_pct=0.035, stop_pct=0.025, horizon_bars=5)
    assert len(targets) == len(sample_ohlcv)
    unique_vals = set(targets.unique())
    assert unique_vals.issubset({0, 1})
    assert targets.name == "is_winning_wave"


def test_build_feature_matrix(sample_ohlcv):
    congress = {"has_recent_buy": True, "buy_count": 2}
    insider = {"has_recent_buy": True, "has_cluster_buy": True, "insider_score": 85.0}
    sentiment = {"sentiment_score": 0.45, "buzz_zscore": 1.8}

    matrix = build_feature_matrix(sample_ohlcv, congress, insider, sentiment)
    for col in FEATURE_COLUMNS:
        assert col in matrix.columns, f"Column {col} missing in feature matrix"
    
    assert not matrix[FEATURE_COLUMNS].isna().any().any()
