import pytest
import pandas as pd
import numpy as np
from src.models.forecasting.training import (
    build_feature_columns,
    split_train_validation,
    prepare_xgboost_data,
    compute_metric_bundle
)

def test_build_feature_columns():
    df = pd.DataFrame({"id": [1], "sales": [1], "d": [1], "date": [1], "d_num": [1], "feature1": [1]})
    cols = build_feature_columns(df)
    assert cols == ["feature1"]

def test_split_train_validation():
    df = pd.DataFrame({
        "d_num": [1, 2, 3, 4, 5],
        "sales": [10, 20, 30, 40, 50]
    })
    train, val = split_train_validation(df, validation_days=2)
    assert len(train) == 3
    assert len(val) == 2

def test_split_train_validation_fallback():
    # Only 2 unique days
    df = pd.DataFrame({
        "d_num": [1, 2],
        "sales": [10, 20]
    })
    train, val = split_train_validation(df, validation_days=5)
    assert len(train) == 1
    assert len(val) == 1

def test_prepare_xgboost_data():
    df = pd.DataFrame({
        "ds": pd.date_range("2020-01-01", periods=30),
        "y": range(30),
        "product_id": ["A"] * 30,
        "store_id": ["S1"] * 30
    })
    x, y, cols = prepare_xgboost_data(df, product_id="A", store_id="S1", lookback=7)
    assert x.shape == (23, 7)
    assert len(y) == 23
    assert len(cols) == 7

def test_prepare_xgboost_data_empty():
    df = pd.DataFrame({
        "ds": pd.date_range("2020-01-01", periods=5),
        "y": range(5)
    })
    x, y, cols = prepare_xgboost_data(df, lookback=7)
    assert x.shape == (0, 7)
    assert len(y) == 0

def test_compute_metric_bundle():
    actual = np.array([10.0, 20.0])
    predicted = np.array([12.0, 18.0])
    metrics = compute_metric_bundle(actual, predicted)
    assert "rmse" in metrics
    assert "mae" in metrics

from src.models.forecasting.training import engineer_features, prepare_prophet_data, _optuna_lgbm_params

def test_engineer_features():
    long_frame = pd.DataFrame({"id": ["item_1_store_1", "item_1_store_1"], "d_num": [1, 2], "d": ["d_1", "d_2"], "store_id": [1, 1], "item_id": [1, 1], "sales": [10, 15]})
    calendar_df = pd.DataFrame({"d": ["d_1", "d_2"], "wm_yr_wk": ["2020-01-01", "2020-01-02"]})
    prices_df = pd.DataFrame({"store_id": [1, 1], "item_id": [1, 1], "wm_yr_wk": ["2020-01-01", "2020-01-02"], "sell_price": [1.99, 1.99]})
    
    result = engineer_features(long_frame, calendar_df, prices_df)
    
    assert "date" in result.columns
    assert "dayofweek" in result.columns
    assert "sell_price" in result.columns

def test_prepare_prophet_data():
    df = pd.DataFrame({
        "ds": pd.date_range("2020-01-01", periods=10),
        "y": range(10),
        "product_id": ["A"] * 5 + ["B"] * 5,
        "store_id": ["S1"] * 5 + ["S2"] * 5
    })
    
    result_A = prepare_prophet_data(df, product_id="A")
    assert len(result_A) == 5
    assert "ds" in result_A.columns
    assert "y" in result_A.columns
    
    result_B = prepare_prophet_data(df, store_id="S2")
    assert len(result_B) == 5

def test_optuna_lgbm_params_no_optuna_or_zero_trials():
    # Should return defaults when n_trials <= 0
    params = _optuna_lgbm_params(pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), n_trials=0)
    assert "n_estimators" in params
    assert params["n_estimators"] == 800
