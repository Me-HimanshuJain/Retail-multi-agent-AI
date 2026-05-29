"""Simulation control page."""

from __future__ import annotations

import requests
import streamlit as st


def _get_simulation_status() -> dict:
    """Fetch and sanitize the current running status from the backend API."""
    try:
        resp = requests.get("http://localhost:8000/simulation/status", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            
            # Bulletproof parsing
            running = bool(data.get("running", False))
            sim_id = data.get("simulation_id")
            sim_id_str = str(sim_id) if sim_id is not None else None
            
            # Handle both 'total_days' and the older 'days' key from the API
            raw_days = data.get("total_days")
            if raw_days is None:
                raw_days = data.get("days")
                
            try:
                parsed_days = int(raw_days) if raw_days is not None else 0
            except (ValueError, TypeError):
                parsed_days = 0

            return {
                "running": running,
                "simulation_id": sim_id_str,
                "total_days": parsed_days
            }
    except Exception:
        pass
    
    return {"running": False, "simulation_id": None, "total_days": 0}


def _start_simulation(days: int, seed: int) -> dict:
    """Trigger the actual RetailSimulator backend."""
    try:
        payload = {"days": int(days), "seed": int(seed), "inject_disruptions": False}
        resp = requests.post("http://localhost:8000/simulation/start", json=payload, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"API Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}


def show_simulation_page() -> None:
    st.title("Simulation Control Panel")
    
    status = _get_simulation_status()
    is_running = status.get("running", False)
    
    # Final safety net before the if-statement
    try:
        total_days = int(status.get("total_days", 0))
    except (ValueError, TypeError):
        total_days = 0
    
    # 1. Current Status Banner
    if is_running:
        st.success(f"🟢 Engine is currently RUNNING. ID: {status.get('simulation_id')} (Duration: {total_days} days)")
    else:
        if total_days > 0:
            st.info(f"⚪ Engine is IDLE. Last run completed {total_days} days of simulation.")
        else:
            st.info("⚪ Engine is IDLE. No simulation data loaded.")

    st.markdown("---")
    
    # 2. Control Form
    st.subheader("Configure New Simulation")
    
    with st.form("sim_config"):
        col1, col2 = st.columns(2)
        days = col1.slider("Simulation Duration (Days)", min_value=7, max_value=90, value=30, step=1)
        seed = col2.number_input("Random Seed (for reproducibility)", value=42, step=1)
        
        submit = st.form_submit_button("Launch Retail Simulation", disabled=is_running)
        
        if submit:
            st.info("Starting simulation engine...")
            result = _start_simulation(days, seed)
            
            if "error" in result:
                st.error(f"Failed to start simulation: {result['error']}")
            else:
                st.success("Simulation triggered successfully! Head over to the KPI or Agent tabs to monitor the real-time execution.")
                st.rerun()