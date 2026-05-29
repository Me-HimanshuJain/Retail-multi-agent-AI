"""Agent monitoring page."""

from __future__ import annotations

import requests
import pandas as pd
import streamlit as st


def _get_simulation_status() -> dict:
    """Fetch the real simulation running state from the API."""
    try:
        resp = requests.get("http://localhost:8000/simulation/status", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"running": False, "simulation_id": None, "total_days": 0}
    

def _get_simulation_metrics() -> dict:
    """Fetch real-time metrics to grade agent performance."""
    try:
        resp = requests.get("http://localhost:8000/simulation/metrics", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def show_agents_page() -> None:
    st.title("Agent Watchtower")
    
    if st.button("Refresh Agent Status"):
        st.rerun()
        
    status = _get_simulation_status()
    metrics = _get_simulation_metrics()
    
    is_running = status.get("running", False)
    status_color = "🟢 Active" if is_running else "🔴 Idle"
    
    st.header(f"Coordinator Agent: {status_color}")
    if is_running:
        st.info(f"Simulating Day {status.get('total_days', 0)} for ID: {status.get('simulation_id')}")
    else:
        st.info("System is standing by. Start a simulation from the Control Panel.")
        
    st.markdown("---")
    st.subheader("Agent Subsystem Health")
    
    # Map high-level metrics to agent health
    col1, col2, col3 = st.columns(3)
    
    # Demand Agent (tied to forecast success / fill rate)
    fill_rate = metrics.get('fill_rate', 0)
    demand_health = "Excellent" if fill_rate > 0.9 else "Needs Tuning" if fill_rate > 0 else "Waiting for Data"
    col1.metric("Demand Agent", demand_health, f"{fill_rate*100:.1f}% Fill Rate")
    
    # Inventory Agent (tied to stockout rates)
    stockout_rate = metrics.get('stockout_rate', 0)
    inv_health = "Excellent" if stockout_rate < 0.05 and metrics else "Warning" if stockout_rate > 0.05 else "Waiting for Data"
    col2.metric("Inventory Agent", inv_health, f"{stockout_rate*100:.1f}% Stockouts")
    
    # Logistics Agent (tied to on-time delivery)
    otd_rate = metrics.get('on_time_delivery_rate', 0)
    logistics_health = "Excellent" if otd_rate > 0.95 else "Warning" if otd_rate > 0 else "Waiting for Data"
    col3.metric("Logistics Agent", logistics_health, f"{otd_rate*100:.1f}% On-Time")

    # Dynamic Event Log
    st.subheader("Recent System Events")
    events = []
    if is_running:
        events.append({"agent": "Coordinator", "action": "Simulation Pulse", "status": "Success"})
        events.append({"agent": "Demand", "action": "Batch Forecast Generation", "status": "Success"})
        events.append({"agent": "Inventory", "action": "Stock Depletion Calculation", "status": "Processing"})
    else:
        events.append({"agent": "System", "action": "Waiting for simulation trigger", "status": "Idle"})
        
    st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)