"""Simulation control page."""

from __future__ import annotations

import requests
import streamlit as st


def _get_simulation_status() -> dict:
    try:
        resp = requests.get("http://localhost:8000/simulation/status", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            running = bool(data.get("running", False))
            sim_id_str = str(data.get("simulation_id")) if data.get("simulation_id") else None
            
            raw_days = data.get("total_days") or data.get("days")
            try:
                parsed_days = int(raw_days) if raw_days is not None else 0
            except (ValueError, TypeError):
                parsed_days = 0

            return {"running": running, "simulation_id": sim_id_str, "total_days": parsed_days}
    except Exception:
        pass
    return {"running": False, "simulation_id": None, "total_days": 0}


def _start_simulation(days: int, seed: int) -> dict:
    try:
        payload = {"days": int(days), "seed": int(seed), "inject_disruptions": False}
        resp = requests.post("http://localhost:8000/simulation/start", json=payload, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"API Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}


def _trigger_disruption(disruption_type: str, severity: str) -> None:
    try:
        payload = {"type": disruption_type, "severity": severity}
        requests.post("http://localhost:8000/simulation/disrupt", json=payload, timeout=2)
        st.toast(f"⚡ Injected {disruption_type.replace('_', ' ').title()}!", icon="⚠️")
    except Exception as e:
        st.error(f"Failed to inject chaos: {e}")


def show_simulation_page() -> None:
    st.title("Simulation Control Panel")
    
    status = _get_simulation_status()
    is_running = status.get("running", False)
    
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
        days = col1.slider("Simulation Duration (Days)", min_value=7, max_value=90, value=60, step=1)
        seed = col2.number_input("Random Seed (for reproducibility)", value=42, step=1)
        
        submit = st.form_submit_button("Launch Retail Simulation", disabled=is_running)
        
        if submit:
            st.info("Starting simulation engine...")
            result = _start_simulation(days, seed)
            if "error" in result:
                st.error(f"Failed to start simulation: {result['error']}")
            else:
                st.success("Simulation triggered successfully!")
                st.rerun()

    # 3. Live Chaos Engine (Only appears when running)
    if is_running:
        st.markdown("---")
        st.subheader("🌩️ Live Chaos Engine")
        st.warning("Inject real-time shocks into the running simulation.")
        
        col_chaos1, col_chaos2 = st.columns(2)
        with col_chaos1:
            if st.button("📈 Trigger Viral Trend (400% Demand Spike)", use_container_width=True):
                _trigger_disruption("viral_trend", "high")
        with col_chaos2:
            if st.button("🚢 Trigger Port Strike (12-Day Lead Time)", use_container_width=True):
                _trigger_disruption("supplier_delay", "high")