"""Forecast visualization page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _generate_forecast_data(horizon: int = 14) -> pd.DataFrame:
    return pd.DataFrame({"day": list(range(1, horizon + 1)), "forecast": [100 + i * 2 for i in range(horizon)], "lower": [90 + i * 2 for i in range(horizon)], "upper": [110 + i * 2 for i in range(horizon)]})


def _generate_model_comparison() -> pd.DataFrame:
    return pd.DataFrame({"model": ["Prophet", "XGBoost", "Ensemble"], "mape": [9.2, 8.7, 7.5]})


def _generate_multi_product_forecast() -> pd.DataFrame:
    return pd.DataFrame({"Day 1": [1, 2], "Day 2": [3, 4]})


def show_forecast_page() -> None:
    st.title("Demand Forecasts")
    df = _generate_forecast_data()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["day"], y=df["forecast"], name="Forecast"))
    st.plotly_chart(fig, use_container_width=True)
