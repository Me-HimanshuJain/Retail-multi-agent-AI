from __future__ import annotations

from pathlib import Path

import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.forecasting.xgboost_model import XGBoostForecaster


client = TestClient(app)


def _get_lgb_feature_sample(store: str) -> dict:
    model_path = Path("models") / f"lgb_model_{store}.bin"
    if not model_path.exists():
        pytest.skip(f"Missing LightGBM model for {store}")
    try:
        # Light load only for feature names
        import joblib

        payload = joblib.load(model_path)
        if hasattr(payload, "feature_name"):
            features = list(payload.feature_name())
        elif isinstance(payload, dict) and "feature_names" in payload:
            features = list(payload.get("feature_names", []))
        else:
            features = ["lag_7", "lag_14", "lag_28"]
    except Exception:
        features = ["lag_7", "lag_14", "lag_28"]
    return {f: 1.0 for f in features}


def _get_xgb_feature_sample(store: str) -> dict:
    model_path = Path("models") / f"xgb_model_{store}.json"
    if not model_path.exists():
        return {}
    model = XGBoostForecaster.load(model_path)
    if model.feature_names:
        return {f: 1.0 for f in model.feature_names}
    return {}


def test_forecast_ensemble_endpoint_ca1():
    store = "CA_1"

    if not (Path("models") / f"ensemble_{store}.bin").exists():
        pytest.skip(f"Missing ensemble model for {store}")

    # Obtain a valid token — any authenticated role is sufficient for /forecast/predict
    token_resp = client.post("/auth/token", data={"username": "viewer", "password": "viewer123"})
    assert token_resp.status_code == 200, f"Login failed: {token_resp.text}"
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Prefer XGBoost features when available because ensemble members may expect full feature set
    features = _get_xgb_feature_sample(store) or _get_lgb_feature_sample(store)
    payload = {"features": features, "horizon": 1, "model": "ensemble", "store": store}
    response = client.post("/forecast/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "forecast" in data and isinstance(data["forecast"], list)
    assert len(data["forecast"]) >= 1
