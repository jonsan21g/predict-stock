import os
import pytest
import pandas as pd
import numpy as np
from src.analysis.features import FEATURE_COLUMNS
from src.analysis.wave_classifier import (
    train_wave_model,
    predict_wave_probability,
    score_single_stock
)


def test_train_wave_model_and_inference(tmp_path):
    # Train model to temp file
    temp_model_path = os.path.join(tmp_path, "test_wave_model.joblib")
    
    # Train using small subset of tickers for speed
    train_result = train_wave_model(save_path=temp_model_path, tickers=["NVDA", "MU", "DELL"])
    assert train_result["status"] == "SUCCESS"
    assert os.path.exists(temp_model_path)
    assert train_result["sample_count"] > 100


    # Test single-row inference
    fake_features = pd.DataFrame([{col: np.random.uniform(0, 1) for col in FEATURE_COLUMNS}])
    proba = predict_wave_probability(fake_features, model_path=temp_model_path)
    assert isinstance(proba, float)
    assert 0.0 <= proba <= 1.0


def test_score_single_stock():
    # Test scoring a real watchlist stock
    score_data = score_single_stock("NVDA")
    assert isinstance(score_data, dict)
    assert score_data["ticker"] == "NVDA"
    assert "current_price" in score_data
    assert "composite_score" in score_data
    assert 0 <= score_data["composite_score"] <= 100
    assert "wave_probability" in score_data
    assert "smart_money" in score_data
