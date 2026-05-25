"""Executive KPI page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def _load_kpi_metrics() -> dict:
    return {
        "total_revenue": 120000.0,
        "total_profit": 25000.0,
        "fill_rate": 0.96,
        "stockout_rate": 0.02,
        "on_time_delivery_rate": 0.98,
    }


def _generate_trend_data(days: int = 30) -> pd.DataFrame:
    return pd.DataFrame({"day": list(range(1, days + 1)), "revenue": [1000 + i * 20 for i in range(days)]})


def _generate_stockout_data() -> pd.DataFrame:
    return pd.DataFrame({"product": ["Milk", "Bread", "Eggs"], "stockouts": [2, 1, 0]})


def _generate_category_data() -> pd.DataFrame:
    return pd.DataFrame({"category": ["Grocery", "Fresh", "Household"], "revenue": [50000, 30000, 20000]})


def _generate_agent_summary() -> pd.DataFrame:
    return pd.DataFrame({"agent": ["Demand", "Inventory", "Pricing"], "success_rate": [0.97, 0.95, 0.93]})


def show_kpi_page() -> None:
    st.title("Executive Overview")
    metrics = _load_kpi_metrics()
    st.metric("Revenue", f"${metrics['total_revenue']:,.0f}")
    st.metric("Profit", f"${metrics['total_profit']:,.0f}")
    trend = _generate_trend_data(30)
    st.plotly_chart(px.line(trend, x="day", y="revenue"), use_container_width=True)
