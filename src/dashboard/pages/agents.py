"""Agent monitoring page."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def _generate_agent_statuses() -> dict:
    return {name: "ready" for name in ["Demand", "Inventory", "Pricing", "Supplier", "Procurement", "Warehouse", "Logistics", "Customer", "Coordinator"]}


def _generate_decisions(agent_filter: list) -> pd.DataFrame:
    return pd.DataFrame({"agent": ["Demand", "Inventory"], "action": ["forecast", "restock"], "success": [True, True]})


def _generate_agent_stats() -> pd.DataFrame:
    return pd.DataFrame({"agent": ["Demand", "Inventory", "Pricing"], "success_rate": [0.98, 0.96, 0.94]})


def _generate_event_distribution() -> pd.DataFrame:
    return pd.DataFrame({"event": ["forecast", "restock"], "count": [20, 10]})


def show_agents_page() -> None:
    st.title("Agent Watchtower")
    st.dataframe(_generate_agent_stats())
