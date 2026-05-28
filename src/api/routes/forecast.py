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
from src.models.forecasting.ensemble import ForecastEnsemble

router = APIRouter(prefix="/forecast", tags=["Forecast"])


class ForecastRequest(BaseModel):
    features: Dict[str, float]
    horizon: int = Field(default=1, ge=1, le=28)
    model: str = Field(default="auto", pattern="^(auto|xgb|lgbm|ensemble)$")
    store: str = Field(default="CA_1")


class ForecastResponse(BaseModel):
    model: str
    forecast: List[float]
    lower: List[float]
    upper: List[float]


def _load_xgb_model(store: str) -> XGBoostForecaster:
    model_path = Path("models") / f"xgb_model_{store}.bin"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"XGBoost model artifact not found at {model_path}")
    return XGBoostForecaster.load(model_path)


def _load_lgb_model(store: str) -> object:
    model_path = Path("models") / f"lgb_model_{store}.bin"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"LightGBM model artifact not found at {model_path}")
    try:
        return Booster(model_file=str(model_path))
    except LightGBMError:
        return joblib.load(model_path)


def _load_ensemble(store: str) -> ForecastEnsemble:
    model_path = Path("models") / f"ensemble_{store}.bin"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Ensemble artifact not found at {model_path}")
    return ForecastEnsemble.load(model_path)


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

    store = request.store
    requested = request.model

    # Ensemble preferred when auto and available
    if requested == "ensemble" or (requested == "auto" and (Path("models") / f"ensemble_{store}.bin").exists()):
        ensemble = _load_ensemble(store)
        member_forecasts: Dict[str, np.ndarray] = {}
        # For each expected member, attempt to load and predict
        members = list(ensemble.weights.keys()) if ensemble.weights else list(ensemble.models.keys())
        for member in members:
            key = member.lower()
            if "xgb" in key:
                try:
                    xgb = _load_xgb_model(store)
                    member_forecasts[member] = np.asarray(xgb.predict(frame)["median"], dtype=float)
                except HTTPException:
                    continue
            elif "lgb" in key:
                try:
                    lgbm = _load_lgb_model(store)
                    features = list(lgbm.feature_name()) if hasattr(lgbm, "feature_name") else []
                    aligned = pd.DataFrame([{feature: float(request.features.get(feature, 0.0)) for feature in features}])
                    member_forecasts[member] = np.asarray(lgbm.predict(aligned), dtype=float)
                except HTTPException:
                    continue
            else:
                # Unknown member type; skip
                continue

        if not member_forecasts:
            raise HTTPException(status_code=404, detail=f"No ensemble members available for store {store}")

        combined = ensemble.combine(member_forecasts)
        median = combined["median"].astype(float).tolist()
        lower = combined["p10"].astype(float).tolist()
        upper = combined["p90"].astype(float).tolist()
        return ForecastResponse(model=f"ensemble_{store}", forecast=median, lower=lower, upper=upper)

    # XGBoost path
    if requested in {"auto", "xgb"} and (Path("models") / f"xgb_model_{store}.bin").exists():
        model = _load_xgb_model(store)
        prediction = model.predict(frame)
        median = prediction["median"].astype(float).tolist()
        lower = prediction["p10"].astype(float).tolist()
        upper = prediction["p90"].astype(float).tolist()
        return ForecastResponse(model=f"xgb_model_{store}", forecast=median, lower=lower, upper=upper)

    # LightGBM fallback
    if requested in {"auto", "lgbm"} and (Path("models") / f"lgb_model_{store}.bin").exists():
        model = _load_lgb_model(store)
        features = list(model.feature_name()) if hasattr(model, "feature_name") else []
        aligned = pd.DataFrame([{feature: float(request.features.get(feature, 0.0)) for feature in features}])
        median_np = model.predict(aligned)
        median = np.asarray(median_np, dtype=float)
        spread = np.maximum(np.abs(median) * 0.08, 1e-6)
        lower = (median - spread).tolist()
        upper = (median + spread).tolist()
        return ForecastResponse(model=f"lgb_model_{store}", forecast=median.tolist(), lower=lower, upper=upper)

    raise HTTPException(status_code=404, detail="Requested model artifact is not available for the given store")
