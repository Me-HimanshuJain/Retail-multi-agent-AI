"""Forecast training helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd


def _generate_mock_data(days: int = 365) -> pd.DataFrame:
    start = datetime(2023, 1, 1)
    rows = []
    for index in range(days):
        rows.append({"ds": start + timedelta(days=index), "y": 100 + index % 10, "product_id": 1, "store_id": 1})
    return pd.DataFrame(rows)


def prepare_prophet_data(df: pd.DataFrame, product_id: int, store_id: int) -> pd.DataFrame:
    subset = df[(df["product_id"] == product_id) & (df["store_id"] == store_id)].copy()
    return subset[["ds", "y"]].sort_values("ds")


def prepare_xgboost_data(df: pd.DataFrame, product_id: int, store_id: int, lookback: int = 28) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    subset = df[(df["product_id"] == product_id) & (df["store_id"] == store_id)].copy()
    values = subset["y"].to_numpy(dtype=float)
    if len(values) <= lookback:
        return np.empty((0, lookback)), np.empty((0,)), [f"lag_{i}" for i in range(lookback)]
    X, y = [], []
    for idx in range(lookback, len(values)):
        X.append(values[idx - lookback:idx])
        y.append(values[idx])
    feature_cols = [f"lag_{i}" for i in range(lookback)]
    return np.asarray(X), np.asarray(y), feature_cols
