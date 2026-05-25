"""Inventory monitoring page."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def _color_stock_status(val):
    return ""


def _generate_inventory_data(location_type: str, location_id: int) -> pd.DataFrame:
    return pd.DataFrame({"product": [f"Product {i}" for i in range(1, 11)], "stock": [100 - i * 5 for i in range(10)], "status": ["ok"] * 10})


def _generate_alerts() -> pd.DataFrame:
    return pd.DataFrame({"product": ["Product 1", "Product 2"], "severity": ["high", "medium"]})


def _generate_abc_data() -> pd.DataFrame:
    return pd.DataFrame({"product": ["A", "B", "C"], "class": ["A", "B", "C"]})


def _generate_expiry_data() -> pd.DataFrame:
    return pd.DataFrame({"product": ["Milk"], "days_remaining": [3]})


def show_inventory_page() -> None:
    st.title("Inventory Monitor")
    st.dataframe(_generate_inventory_data("Store", 1))
