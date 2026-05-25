"""Logistics page."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def _generate_shipments() -> pd.DataFrame:
    return pd.DataFrame({"shipment_id": [1, 2, 3], "status": ["in_transit", "delivered", "delayed"]})


def _generate_route_stats() -> pd.DataFrame:
    return pd.DataFrame({"route": ["A", "B"], "savings_pct": [12.0, 8.5]})


def show_logistics_page() -> None:
    st.title("Logistics Map")
    st.dataframe(_generate_route_stats())
