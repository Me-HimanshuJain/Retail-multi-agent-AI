"""Streamlit dashboard entry point."""

from __future__ import annotations

import streamlit as st

from src.dashboard.pages.agents import show_agents_page
from src.dashboard.pages.forecast import show_forecast_page
from src.dashboard.pages.inventory import show_inventory_page
from src.dashboard.pages.kpi import show_kpi_page
from src.dashboard.pages.logistics import show_logistics_page
from src.dashboard.pages.simulation_control import show_simulation_page

st.set_page_config(page_title="Retail Multi-Agent AI", layout="wide")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Executive Overview",
        "📈 Demand Forecasts",
        "📦 Inventory Monitor",
        "🤖 Agent Watchtower",
        "🚚 Logistics Map",
        "🎮 Simulation Control",
    ],
)

if page == "📊 Executive Overview":
    show_kpi_page()
elif page == "📈 Demand Forecasts":
    show_forecast_page()
elif page == "📦 Inventory Monitor":
    show_inventory_page()
elif page == "🤖 Agent Watchtower":
    show_agents_page()
elif page == "🚚 Logistics Map":
    show_logistics_page()
elif page == "🎮 Simulation Control":
    show_simulation_page()
