"""Forecast API routes backed by trained model artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from lightgbm import Booster
from lightgbm.basic import LightGBMError

from src.models.forecasting.xgboost_model import XGBoostForecaster

router = APIRouter(prefix="/forecast", tags=["Forecast"])


class ForecastRequest(BaseModel):
    features: Dict[str, float]
    horizon: int = Field(default=1, ge=1, le=28)
    model: str = Field(default="auto", pattern="^(auto|xgb|lgbm)$")


class ForecastResponse(BaseModel):
    model: str
    forecast: List[float]
    lower: List[float]
    upper: List[float]


def _load_xgb_model() -> XGBoostForecaster:
    model_path = Path("models") / "xgb_model_CA_1.bin"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model artifact not found at {model_path}")
    return XGBoostForecaster.load(model_path)


def _load_lgb_model() -> object:
    model_path = Path("models") / "lgb_model_CA_1.bin"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model artifact not found at {model_path}")
    try:
        return Booster(model_file=str(model_path))
    except LightGBMError:
        return joblib.load(model_path)


@router.get("/health")
def forecast_health() -> dict:
    return {
        "xgb_model_exists": (Path("models") / "xgb_model_CA_1.bin").exists(),
        "lgbm_model_exists": (Path("models") / "lgb_model_CA_1.bin").exists(),
        "ensemble_model_exists": (Path("models") / "ensemble_CA_1.bin").exists(),
    }


@router.post("/predict", response_model=ForecastResponse)
def predict_forecast(request: ForecastRequest) -> ForecastResponse:
    frame = pd.DataFrame([request.features])

    use_xgb = request.model in {"auto", "xgb"}
    if use_xgb and (Path("models") / "xgb_model_CA_1.bin").exists():
        model = _load_xgb_model()
        prediction = model.predict(frame)
        median = prediction["median"].astype(float).tolist()
        lower = prediction["p10"].astype(float).tolist()
        upper = prediction["p90"].astype(float).tolist()
        return ForecastResponse(model="xgb_model_CA_1", forecast=median, lower=lower, upper=upper)

    if request.model in {"auto", "lgbm"}:
        model = _load_lgb_model()
        features = list(model.feature_name())
        aligned = pd.DataFrame([{feature: float(request.features.get(feature, 0.0)) for feature in features}])
        median_np = model.predict(aligned)
        median = np.asarray(median_np, dtype=float)
        spread = np.maximum(np.abs(median) * 0.08, 1e-6)
        lower = (median - spread).tolist()
        upper = (median + spread).tolist()
        return ForecastResponse(model="lgb_model_CA_1", forecast=median.tolist(), lower=lower, upper=upper)

    raise HTTPException(status_code=404, detail="Requested model artifact is not available")
