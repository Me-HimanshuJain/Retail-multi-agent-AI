"""Streamlit dashboard entry point."""

from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

from src.dashboard.pages.agents import show_agents_page
from src.dashboard.pages.forecast import show_forecast_page
from src.dashboard.pages.inventory import show_inventory_page
from src.dashboard.pages.kpi import show_kpi_page
from src.dashboard.pages.logistics import show_logistics_page
from src.dashboard.pages.simulation_control import show_simulation_page

# Application Constants
ENGINE_VERSION = "v0.9.0"  # Updated to match our new Multi-Agent + Ensemble architecture

# 1. Page Config (Must be first)
st.set_page_config(
    page_title="Retail Multi-Agent AI", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Custom CSS for a clean, edge-to-edge dark mode look
st.markdown("""
    <style>
        /* Hide default Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Tighten up the top padding so content doesn't sit so low */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Style the sidebar darker for sharp contrast */
        [data-testid="stSidebar"] {
            background-color: #09090b;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Build the Premium Sidebar
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #39FF14;'>🧠 Retail AI Core</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Modern Option Menu with neon green accents
    page = option_menu(
        menu_title=None,  # Hide the default title
        options=[
            "Executive Overview", 
            "Demand Forecasts", 
            "Inventory Monitor", 
            "Agent Watchtower", 
            "Logistics Map", 
            "Simulation Control"
        ],
        icons=[
            "bar-chart-line", 
            "graph-up-arrow", 
            "box-seam", 
            "robot", 
            "truck", 
            "sliders"
        ],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#39FF14", "font-size": "18px"}, 
            "nav-link": {
                "font-size": "15px", 
                "text-align": "left", 
                "margin": "0px", 
                "padding": "10px",
                "--hover-color": "#1a1c23"
            },
            "nav-link-selected": {"background-color": "#121418", "border-left": "4px solid #39FF14"},
        }
    )
    
    st.markdown("---")
    # Dynamically inject the version constant
    st.caption(f"Status: **{ENGINE_VERSION} Engine Active** 🟢")

# 4. Route to the correct page
if page == "Executive Overview":
    show_kpi_page()
elif page == "Demand Forecasts":
    show_forecast_page()
elif page == "Inventory Monitor":
    show_inventory_page()
elif page == "Agent Watchtower":
    show_agents_page()
elif page == "Logistics Map":
    show_logistics_page()
elif page == "Simulation Control":
    show_simulation_page()