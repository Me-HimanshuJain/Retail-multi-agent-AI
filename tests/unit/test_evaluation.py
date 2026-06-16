import pytest
import numpy as np
import pandas as pd
from src.models.forecasting.evaluation import (
    prediction_interval_coverage_probability,
    mean_prediction_interval_width,
    evaluate_forecast,
    evaluate_all_models,
    compare_models,
    calculate_residuals,
    bias,
    tracking_signal
)

def test_prediction_interval():
    actual = np.array([10, 20, 30])
    lower = np.array([5, 15, 25])
    upper = np.array([15, 25, 35])
    
    assert prediction_interval_coverage_probability(actual, lower, upper) == 1.0
    assert mean_prediction_interval_width(lower, upper) == 10.0

def test_evaluate_forecast():
    actual = np.array([10, 20, 30])
    predicted = np.array([10, 20, 30])
    lower = np.array([5, 15, 25])
    upper = np.array([15, 25, 35])
    
    metrics = evaluate_forecast(actual, predicted, lower, upper)
    assert "picp" in metrics
    assert "mpiw" in metrics
    assert metrics["picp"] == 1.0
    assert metrics["mpiw"] == 10.0

def test_evaluate_all_models():
    models = {"xgb": object(), "lgbm": object()}
    actual = np.array([10, 20, 30])
    df = evaluate_all_models(models, actual)
    assert len(df) == 2
    assert "model" in df.columns
    assert "mape" in df.columns

def test_compare_models():
    df = pd.DataFrame({"model": ["A", "B"], "mape": [2.0, 1.0]})
    sorted_df = compare_models(df)
    assert sorted_df.iloc[0]["model"] == "B"

def test_calculate_residuals():
    actual = np.array([10, 20])
    predicted = np.array([8, 22])
    res = calculate_residuals(actual, predicted)
    np.testing.assert_array_equal(res, np.array([2, -2]))

def test_bias():
    actual = np.array([10, 20])
    predicted = np.array([8, 22])
    b = bias(actual, predicted)
    assert b == 0.0

def test_tracking_signal():
    actual = np.array([10, 20, 30])
    predicted = np.array([8, 22, 28])
    ts = tracking_signal(actual, predicted)
    # residuals = 2, -2, 2 -> sum = 2
    # mad = (2 + 2 + 2) / 3 = 2
    # tracking_signal = 2 / 2 = 1.0
    assert ts == 1.0

def test_tracking_signal_zero_mad():
    actual = np.array([10, 20])
    predicted = np.array([10, 20])
    # sum = 0, mad = 0
    # should fallback to mad=1.0 -> 0.0 / 1.0 = 0.0
    ts = tracking_signal(actual, predicted)
    assert ts == 0.0
