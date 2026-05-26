"""Forecast visualization page."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lightgbm import Booster
from lightgbm.basic import LightGBMError

from src.models.forecasting.ensemble import ForecastEnsemble
from src.models.forecasting.xgboost_model import XGBoostForecaster


def _build_latest_feature_row(columns: list[str]) -> pd.DataFrame:
    # This minimal feature row should be replaced by real feature service integration.
    return pd.DataFrame([{column: 10.0 for column in columns}])


def _load_trained_predictions() -> tuple[pd.DataFrame, pd.DataFrame]:
    xgb_path = Path("models/xgb_model_CA_1.bin")
    xgb_pred = None
    if xgb_path.exists():
        xgb = XGBoostForecaster.load(xgb_path)
        xgb_columns = xgb.feature_names or [
            "lag_7",
            "lag_14",
            "lag_28",
            "rmean_28_7",
            "rmean_28_14",
            "rmean_28_28",
            "rstd_28_7",
            "rstd_28_14",
            "rstd_28_28",
        ]
        xgb_features = _build_latest_feature_row(xgb_columns)
        xgb_pred = xgb.predict(xgb_features)

    try:
        lgb = Booster(model_file="models/lgb_model_CA_1.bin")
    except LightGBMError:
        lgb = joblib.load("models/lgb_model_CA_1.bin")
    lgb_columns = list(lgb.feature_name())
    lgb_features = _build_latest_feature_row(lgb_columns)
    lgb_pred = lgb.predict(lgb_features[lgb_columns])

    if xgb_pred is not None:
        ensemble = ForecastEnsemble(weights={"xgb": 0.5, "lgb": 0.5})
        combined = ensemble.combine({"xgb": xgb_pred["median"], "lgb": lgb_pred})
        xgb_point = float(xgb_pred["median"][0])
    else:
        combined = {
            "median": pd.Series(lgb_pred).to_numpy(dtype=float),
            "p10": (pd.Series(lgb_pred) * 0.92).to_numpy(dtype=float),
            "p90": (pd.Series(lgb_pred) * 1.08).to_numpy(dtype=float),
        }
        xgb_point = float("nan")

    forecast = pd.DataFrame(
        {
            "day": [1],
            "forecast": combined["median"],
            "lower": combined["p10"],
            "upper": combined["p90"],
        }
    )
    model_cmp = pd.DataFrame(
        {
            "model": ["XGBoost", "LightGBM", "Ensemble"],
            "prediction": [xgb_point, float(lgb_pred[0]), float(combined["median"][0])],
        }
    )
    return forecast, model_cmp


def _generate_multi_product_forecast(forecast_value: float) -> pd.DataFrame:
    return pd.DataFrame({"product": ["CA_1_item_1", "CA_1_item_2"], "day_1_forecast": [forecast_value, forecast_value * 0.92]})


def show_forecast_page() -> None:
    st.title("Demand Forecasts")
    try:
        df, model_cmp = _load_trained_predictions()
    except FileNotFoundError as exc:
        st.error(f"Missing model artifact: {exc}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["day"], y=df["forecast"], name="Forecast"))
    fig.add_trace(go.Scatter(x=df["day"], y=df["lower"], name="P10", line={"dash": "dot"}))
    fig.add_trace(go.Scatter(x=df["day"], y=df["upper"], name="P90", line={"dash": "dot"}))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Model Predictions")
    st.dataframe(model_cmp, use_container_width=True)
    st.subheader("Inventory-linked Forecast")
    st.dataframe(_generate_multi_product_forecast(float(df["forecast"].iloc[0])), use_container_width=True)

