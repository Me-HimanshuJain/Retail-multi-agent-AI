"""Integration tests for real forecasting artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models.forecasting.evaluation import evaluate_forecast
from src.models.forecasting.xgboost_model import XGBoostForecaster


def test_xgb_artifact_loads_and_predicts() -> None:
    model_path = Path("models") / "xgb_model_CA_1.bin"
    if not model_path.exists():
        pytest.skip(f"Missing artifact: {model_path}")

    model = XGBoostForecaster.load(model_path)
    frame = pd.DataFrame(
        [
            {
                "lag_7": 11.0,
                "lag_14": 12.0,
                "lag_28": 13.0,
                "rmean_28_7": 10.5,
                "rmean_28_14": 10.0,
                "rmean_28_28": 9.8,
                "rstd_28_7": 1.2,
                "rstd_28_14": 1.6,
                "rstd_28_28": 2.1,
            }
        ]
    )
    prediction = model.predict(frame)
    assert prediction["median"].shape[0] == 1
    assert float(prediction["p90"][0]) >= float(prediction["p10"][0])


def test_evaluate_forecast_metrics_real_values() -> None:
    actual = np.array([10.0, 12.0, 13.0])
    predicted = np.array([9.5, 12.2, 12.8])
    metrics = evaluate_forecast(actual, predicted)
    assert metrics["rmse"] > 0
    assert metrics["mae"] > 0
    assert metrics["mape"] >= 0
