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


def _available_stores() -> list[str]:
    stores = []
    for path in Path("models").glob("lgb_model_*.bin"):
        store = path.stem.replace("lgb_model_", "")
        stores.append(store)
    return sorted(set(stores))


def _load_models(store_id: str) -> tuple[object, XGBoostForecaster | None]:
    try:
        lgb = Booster(model_file=f"models/lgb_model_{store_id}.bin")
    except LightGBMError:
        lgb = joblib.load(f"models/lgb_model_{store_id}.bin")

    xgb_path = Path(f"models/xgb_model_{store_id}.bin")
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


def _load_trained_predictions(store_id: str, horizon: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    lgb, xgb = _load_models(store_id=store_id)
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
            # Prefer trained ensemble weights when available
            ensemble_path = Path(f"models/ensemble_{store_id}.bin")
            if ensemble_path.exists():
                try:
                    ensemble = ForecastEnsemble.load(ensemble_path)
                    member_map = {name: pd.Series([xgb_point]).to_numpy() if "xgb" in name.lower() else pd.Series([lgb_point]).to_numpy() for name in ensemble.weights.keys()}
                    combined = ensemble.combine(member_map)
                    forecast_val = float(combined["median"][0])
                    lower = float(combined["p10"][0])
                    upper = float(combined["p90"][0])
                except Exception:
                    # Fallback to equal-weight combine if ensemble artifact fails
                    ensemble = ForecastEnsemble(weights={"xgb": 0.5, "lgb": 0.5})
                    combined = ensemble.combine({"xgb": pd.Series([xgb_point]).to_numpy(), "lgb": pd.Series([lgb_point]).to_numpy()})
                    forecast_val = float(combined["median"][0])
                    lower = float(combined["p10"][0])
                    upper = float(combined["p90"][0])
        else:
            forecast_val = lgb_point
            lower = lgb_point * 0.92
            upper = lgb_point * 1.08

        rows.append({"store_id": store_id, "day": day, "forecast": forecast_val, "lower": lower, "upper": upper})
        _roll_feature_state(state, forecast_val)

    forecast = pd.DataFrame(rows)
    model_cmp = pd.DataFrame(
        {
            "model": ["XGBoost", "LightGBM", "Ensemble"],
            "prediction": [float(pd.Series(xgb_vals).mean()) if xgb_vals else float("nan"), float(pd.Series(lgb_vals).mean()), float(forecast["forecast"].mean())],
            "store_id": [store_id, store_id, store_id],
        }
    )
    return forecast, model_cmp


def _generate_multi_product_forecast(store_id: str, forecast_value: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "store_product": [f"{store_id}_item_1", f"{store_id}_item_2"],
            "day_1_forecast": [forecast_value, forecast_value * 0.92],
        }
    )


def show_forecast_page() -> None:
    st.title("Demand Forecasts")
    stores = _available_stores()
    if not stores:
        st.error("No LightGBM store artifacts found in models/.")
        return

    selected_stores = st.multiselect("Select Stores", options=stores, default=stores[: min(3, len(stores))])
    if not selected_stores:
        st.info("Select at least one store to render forecasts.")
        return

    horizon = st.slider("Forecast Horizon (days)", min_value=1, max_value=28, value=14)

    forecast_frames = []
    model_cmp_frames = []
    product_frames = []
    for store_id in selected_stores:
        try:
            df, model_cmp = _load_trained_predictions(store_id=store_id, horizon=horizon)
        except FileNotFoundError as exc:
            st.warning(f"Skipping {store_id}: missing model artifact ({exc})")
            continue
        forecast_frames.append(df)
        model_cmp_frames.append(model_cmp)
        product_frames.append(_generate_multi_product_forecast(store_id=store_id, forecast_value=float(df["forecast"].iloc[0])))

    if not forecast_frames:
        st.error("No forecasts could be produced for the selected stores.")
        return

    all_forecasts = pd.concat(forecast_frames, ignore_index=True)
    all_model_cmp = pd.concat(model_cmp_frames, ignore_index=True)
    all_products = pd.concat(product_frames, ignore_index=True)

    fig = go.Figure()
    for store_id in selected_stores:
        subset = all_forecasts[all_forecasts["store_id"] == store_id]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(x=subset["day"], y=subset["forecast"], name=f"{store_id} Forecast"))
        fig.add_trace(go.Scatter(x=subset["day"], y=subset["lower"], name=f"{store_id} P10", line={"dash": "dot"}))
        fig.add_trace(go.Scatter(x=subset["day"], y=subset["upper"], name=f"{store_id} P90", line={"dash": "dot"}))

    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Model Predictions")
    st.dataframe(all_model_cmp, use_container_width=True)
    st.subheader("Inventory-linked Forecast")
    st.dataframe(all_products, use_container_width=True)

