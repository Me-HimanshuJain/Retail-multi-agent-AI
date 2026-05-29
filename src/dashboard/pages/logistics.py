"""Logistics page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from sqlalchemy import text

from src.core.database import SessionLocal


def _get_delivery_metrics() -> float:
    """Fetch real on-time delivery rate from the simulation metrics."""
    try:
        resp = requests.get("http://localhost:8000/simulation/metrics", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("on_time_delivery_rate", 0.0)
    except Exception:
        pass
    return 0.0


def _load_regional_inventory() -> pd.DataFrame:
    """Aggregate real inventory data by geographic region."""
    db = SessionLocal()
    try:
        query = """
        SELECT s.region, SUM(i.quantity) as total_stock, COUNT(DISTINCT s.id) as store_count
        FROM inventory_snapshots i
        JOIN stores s ON i.location_id = s.id
        WHERE i.location_type = 'store'
        GROUP BY s.region
        """
        return pd.read_sql(text(query), db.bind)
    except Exception as e:
        return pd.DataFrame()
    finally:
        db.close()


def show_logistics_page() -> None:
    st.title("Supply Chain & Logistics")
    
    if st.button("Refresh Logistics Data"):
        st.rerun()

    col1, col2 = st.columns(2)
    delivery_rate = _get_delivery_metrics()
    
    col1.metric("Network On-Time Delivery", f"{delivery_rate * 100:.1f}%")
    
    regional_df = _load_regional_inventory()
    if not regional_df.empty:
        total_network_stock = regional_df['total_stock'].sum()
        col2.metric("Total Network Stock (Units)", f"{total_network_stock:,}")
        
        st.markdown("---")
        st.subheader("Regional Warehouse Distribution")
        
        fig = px.pie(
            regional_df, 
            values='total_stock', 
            names='region', 
            title="Stock Distribution by State",
            hole=0.4,
            color_discrete_sequence=["#0068c9", "#83c9ff", "#ff2b2b"]
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Regional Breakdown")
        st.dataframe(
            regional_df.rename(columns={"region": "State", "total_stock": "Total Units", "store_count": "Active Stores"}),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No regional data found. Please run the database seeder.")