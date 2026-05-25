"""Simulation control page."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def _get_progress_data() -> dict:
    return {"progress": 0, "current_day": 0, "total_days": 30}


def _generate_daily_progress(current_day: int) -> pd.DataFrame:
    return pd.DataFrame({"day": list(range(1, current_day + 1)), "progress": [i / max(current_day, 1) for i in range(1, current_day + 1)]})


def _generate_history() -> pd.DataFrame:
    return pd.DataFrame({"simulation": ["sim-1", "sim-2"], "days": [7, 14]})


def show_simulation_page() -> None:
    st.title("Simulation Control")
    st.dataframe(_generate_history())
