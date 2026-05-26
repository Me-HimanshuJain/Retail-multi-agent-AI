"""Integration tests for real forecasting artifacts."""

from __future__ import annotations

from pathlib import Path

import json
import joblib
import numpy as np
import pandas as pd
import pytest
from lightgbm import Booster
from lightgbm.basic import LightGBMError

from src.models.forecasting.evaluation import evaluate_forecast
from src.models.forecasting.xgboost_model import XGBoostForecaster


def test_lgbm_ca1_artifact_loads_and_predicts() -> None:
    model_path = Path("models") / "lgb_model_CA_1.bin"
    if not model_path.exists():
        pytest.skip(f"Missing artifact: {model_path}")

    try:
        model = Booster(model_file=str(model_path))
    except LightGBMError:
        model = joblib.load(model_path)

    feature_names = list(model.feature_name())
    frame = pd.DataFrame([{feature: 1.0 for feature in feature_names}])
    prediction = model.predict(frame)
    assert len(prediction) == 1
    assert not np.isnan(float(prediction[0]))


def test_ca1_metrics_json_has_required_fields() -> None:
    metrics_path = Path("models") / "lgb_model_CA_1.metrics.json"
    if not metrics_path.exists():
        pytest.skip(f"Missing metrics file: {metrics_path}")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    for required in ["rmse", "mae", "mape", "wrmsse", "training_time_sec"]:
        assert required in metrics
        assert float(metrics[required]) >= 0.0


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
