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
