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


def _load_models() -> tuple[object, XGBoostForecaster | None]:
    try:
        lgb = Booster(model_file="models/lgb_model_CA_1.bin")
    except LightGBMError:
        lgb = joblib.load("models/lgb_model_CA_1.bin")

    xgb_path = Path("models/xgb_model_CA_1.bin")
    xgb = XGBoostForecaster.load(xgb_path) if xgb_path.exists() else None
    return lgb, xgb


def _roll_feature_state(state: dict[str, float], predicted: float) -> None:
    lag_14 = state.get("lag_14", predicted)
    lag_7 = state.get("lag_7", predicted)
    state["lag_28"] = lag_14
    state["lag_14"] = lag_7
    state["lag_7"] = predicted

    lag_values = [state.get("lag_7", predicted), state.get("lag_14", predicted), state.get("lag_28", predicted)]
    mean_val = float(sum(lag_values) / len(lag_values))
    spread = float(max(lag_values) - min(lag_values))
    for name in ["rmean_28_7", "rmean_28_14", "rmean_28_28"]:
        state[name] = mean_val
    for name in ["rstd_28_7", "rstd_28_14", "rstd_28_28"]:
        state[name] = spread / 3.0


def _load_trained_predictions(horizon: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    lgb, xgb = _load_models()
    state = {
        "lag_7": 10.0,
        "lag_14": 10.0,
        "lag_28": 10.0,
        "rmean_28_7": 10.0,
        "rmean_28_14": 10.0,
        "rmean_28_28": 10.0,
        "rstd_28_7": 1.0,
        "rstd_28_14": 1.0,
        "rstd_28_28": 1.0,
    }

    rows = []
    xgb_vals = []
    lgb_vals = []

    for day in range(1, horizon + 1):
        lgb_columns = list(lgb.feature_name())
        lgb_features = pd.DataFrame([{column: float(state.get(column, 0.0)) for column in lgb_columns}])
        lgb_point = float(lgb.predict(lgb_features[lgb_columns])[0])
        lgb_vals.append(lgb_point)

        xgb_point = None
        if xgb is not None:
            xgb_columns = xgb.feature_names or lgb_columns
            xgb_features = pd.DataFrame([{column: float(state.get(column, 0.0)) for column in xgb_columns}])
            xgb_pred = xgb.predict(xgb_features)
            xgb_point = float(xgb_pred["median"][0])
            xgb_vals.append(xgb_point)

        if xgb_point is not None:
            ensemble = ForecastEnsemble(weights={"xgb": 0.5, "lgb": 0.5})
            combined = ensemble.combine({"xgb": pd.Series([xgb_point]).to_numpy(), "lgb": pd.Series([lgb_point]).to_numpy()})
            forecast_val = float(combined["median"][0])
            lower = float(combined["p10"][0])
            upper = float(combined["p90"][0])
        else:
            forecast_val = lgb_point
            lower = lgb_point * 0.92
            upper = lgb_point * 1.08

        rows.append({"day": day, "forecast": forecast_val, "lower": lower, "upper": upper})
        _roll_feature_state(state, forecast_val)

    forecast = pd.DataFrame(rows)
    model_cmp = pd.DataFrame(
        {
            "model": ["XGBoost", "LightGBM", "Ensemble"],
            "prediction": [float(pd.Series(xgb_vals).mean()) if xgb_vals else float("nan"), float(pd.Series(lgb_vals).mean()), float(forecast["forecast"].mean())],
        }
    )
    return forecast, model_cmp


def _generate_multi_product_forecast(forecast_value: float) -> pd.DataFrame:
    return pd.DataFrame({"product": ["CA_1_item_1", "CA_1_item_2"], "day_1_forecast": [forecast_value, forecast_value * 0.92]})


def show_forecast_page() -> None:
    st.title("Demand Forecasts")
    horizon = st.slider("Forecast Horizon (days)", min_value=1, max_value=28, value=14)
    try:
        df, model_cmp = _load_trained_predictions(horizon=horizon)
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

