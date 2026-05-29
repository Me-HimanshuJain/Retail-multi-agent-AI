"""Executive KPI page."""

from __future__ import annotations

import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text
from src.core.database import SessionLocal


def _load_kpi_metrics() -> dict:
    """Fetch live simulation metrics from the FastAPI backend."""
    try:
        resp = requests.get("http://localhost:8000/simulation/metrics", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    
    return {
        "total_revenue": 0.0,
        "total_profit": 0.0,
        "fill_rate": 0.0,
        "stockout_rate": 0.0,
        "on_time_delivery_rate": 0.0,
    }


def _load_real_inventory() -> pd.DataFrame:
    """Query the local database for actual store inventory distributions."""
    db = SessionLocal()
    try:
        query = """
        SELECT s.name as store, p.category, SUM(i.quantity) as total_quantity
        FROM inventory_snapshots i
        JOIN stores s ON i.location_id = s.id
        JOIN products p ON i.product_id = p.id
        WHERE i.location_type = 'store'
        GROUP BY s.name, p.category
        """
        return pd.read_sql(text(query), db.bind)
    except Exception:
        return pd.DataFrame()
    finally:
        db.close()


def show_kpi_page() -> None:
    st.title("Executive Overview")
    
    if st.button("Refresh Live Metrics"):
        st.rerun()

    metrics = _load_kpi_metrics()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Revenue", f"${metrics.get('total_revenue', 0):,.2f}")
    col2.metric("Profit", f"${metrics.get('total_profit', 0):,.2f}")
    col3.metric("Fill Rate", f"{metrics.get('fill_rate', 0)*100:.1f}%")
    
    col4, col5 = st.columns(2)
    col4.metric("Stockout Rate", f"{metrics.get('stockout_rate', 0)*100:.1f}%")
    col5.metric("On-Time Delivery", f"{metrics.get('on_time_delivery_rate', 0)*100:.1f}%")

    st.markdown("---")
    st.subheader("Current Inventory Levels by Store")
    
    inv_df = _load_real_inventory()
    if not inv_df.empty:
        fig = px.bar(
            inv_df, 
            x="store", 
            y="total_quantity", 
            color="category", 
            barmode="group",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No inventory data found. Ensure the database is seeded and running.")