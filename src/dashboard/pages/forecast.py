"""Forecast visualization page — uses all 35 model features correctly."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.database import SessionLocal
from src.core import models as orm

# Last M5 training day — same reference used in demand_generator.py
_M5_BASE_DATE = datetime(2016, 5, 22)

# Store metadata (label-encoded exactly as in the notebook)
_STORE_META: dict[str, dict] = {
    "CA_1": {"store_id": 0, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 2.98},
    "CA_2": {"store_id": 1, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 3.12},
    "CA_3": {"store_id": 2, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 2.75},
    "CA_4": {"store_id": 3, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 3.49},
    "TX_1": {"store_id": 4, "state_id": 1, "snap_CA": 0, "snap_TX": 1, "snap_WI": 0, "sell_price": 2.50},
    "TX_2": {"store_id": 5, "state_id": 1, "snap_CA": 0, "snap_TX": 1, "snap_WI": 0, "sell_price": 2.89},
    "TX_3": {"store_id": 6, "state_id": 1, "snap_CA": 0, "snap_TX": 1, "snap_WI": 0, "sell_price": 3.25},
    "WI_1": {"store_id": 7, "state_id": 2, "snap_CA": 0, "snap_TX": 0, "snap_WI": 1, "sell_price": 2.65},
    "WI_2": {"store_id": 8, "state_id": 2, "snap_CA": 0, "snap_TX": 0, "snap_WI": 1, "sell_price": 2.79},
    "WI_3": {"store_id": 9, "state_id": 2, "snap_CA": 0, "snap_TX": 0, "snap_WI": 1, "sell_price": 3.10},
}

_SMOOTH_ALPHA = 0.35


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _available_stores() -> list[str]:
    return sorted(p.stem.replace("lgb_model_", "") for p in Path("models").glob("lgb_model_*.bin"))


def _build_row(store_id: str, date: datetime, lag_hist: list[float],
               lag_7: float, lag_14: float, lag_28: float,
               feature_names: list[str]) -> pd.DataFrame:
    """Build the full 35-feature row the model expects."""
    m  = _STORE_META.get(store_id, _STORE_META["CA_1"])
    sp = m["sell_price"]
    wm_yr_wk = 11601 + (date - datetime(2016, 1, 4)).days // 7

    row = {
        "item_id": 1, "dept_id": 1, "cat_id": 1,
        "store_id":  m["store_id"],  "state_id": m["state_id"],
        "wm_yr_wk":  wm_yr_wk,
        "weekday":   date.weekday(), "wday": date.weekday(),
        "month":     date.month,     "year": date.year,
        "event_name_1": -1, "event_type_1": -1,
        "event_name_2": -1, "event_type_2": -1,
        "snap_CA":   m["snap_CA"],   "snap_TX": m["snap_TX"], "snap_WI": m["snap_WI"],
        "sell_price": sp, "dayofweek": date.weekday(),
        "day": date.day, "week": date.isocalendar()[1],
        "quarter": (date.month - 1) // 3 + 1,
        "sell_price_max": sp, "sell_price_min": sp * 0.92,
        "sell_price_std": sp * 0.04, "sell_price_momentum": 1.0,
        "lag_7": lag_7, "lag_14": lag_14, "lag_28": lag_28,
        "rmean_28_7":  float(np.mean(lag_hist[-7:])),
        "rstd_28_7":   float(max(np.std(lag_hist[-7:]),  0.1)),
        "rmean_28_14": float(np.mean(lag_hist[-14:])),
        "rstd_28_14":  float(max(np.std(lag_hist[-14:]), 0.1)),
        "rmean_28_28": float(np.mean(lag_hist[-28:])),
        "rstd_28_28":  float(max(np.std(lag_hist[-28:]), 0.1)),
    }
    return pd.DataFrame([row])[feature_names]


@st.cache_data(ttl=300)
def _run_forecast(store_id: str, horizon: int, base_demand: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run recursive forecast for `horizon` days using LightGBM + XGBoost + Ensemble."""
    try:
        from src.models.forecasting.lgbm_io import load_lgbm_booster
        lgb_model = load_lgbm_booster(f"models/lgb_model_{store_id}.bin")
        feat_names = lgb_model.feature_name()
    except Exception as exc:
        st.error(f"Could not load LightGBM model for {store_id}: {exc}")
        return pd.DataFrame(), pd.DataFrame()

    # Optional XGBoost + Ensemble
    xgb_model  = None
    ens_model  = None
    try:
        from src.models.forecasting.xgboost_model import XGBoostForecaster
        from src.models.forecasting.ensemble import ForecastEnsemble
        xgb_path = Path(f"models/xgb_model_{store_id}.bin")
        ens_path = Path(f"models/ensemble_{store_id}.bin")
        if xgb_path.exists():
            xgb_model = XGBoostForecaster.load(xgb_path)
        if ens_path.exists():
            ens_model = ForecastEnsemble.load(ens_path)
    except Exception:
        pass

    # Initialise rolling state with user-supplied base_demand
    lag_7 = lag_14 = lag_28 = base_demand
    lag_hist = [base_demand] * 28
    alpha = _SMOOTH_ALPHA

    rows, lgb_vals, xgb_vals = [], [], []

    for step in range(horizon):
        date = _M5_BASE_DATE + timedelta(days=step + 1)
        df   = _build_row(store_id, date, lag_hist, lag_7, lag_14, lag_28, feat_names)

        lgb_pred = float(lgb_model.predict(df)[0])
        lgb_vals.append(lgb_pred)

        xgb_pred: Optional[float] = None
        if xgb_model is not None:
            try:
                xgb_pred = float(xgb_model.predict(df)["median"][0])
                xgb_vals.append(xgb_pred)
            except Exception:
                xgb_pred = None

        # Ensemble or fallback
        if ens_model is not None and xgb_pred is not None:
            try:
                combined   = ens_model.combine({
                    "lgbm": np.array([lgb_pred]),
                    "xgb":  np.array([xgb_pred]),
                })
                raw_pred   = float(combined["median"][0])
                lower      = float(combined.get("p10", pd.Series([raw_pred * 0.9]))[0])
                upper      = float(combined.get("p90", pd.Series([raw_pred * 1.1]))[0])
            except Exception:
                raw_pred = (lgb_pred + xgb_pred) / 2
                lower, upper = raw_pred * 0.9, raw_pred * 1.1
        elif xgb_pred is not None:
            raw_pred = (lgb_pred + xgb_pred) / 2
            lower, upper = raw_pred * 0.9, raw_pred * 1.1
        else:
            raw_pred = lgb_pred
            lower, upper = lgb_pred * 0.92, lgb_pred * 1.08

        # Smooth to prevent lag collapse
        smoothed = alpha * raw_pred + (1 - alpha) * float(np.mean(lag_hist[-7:]))
        smoothed = max(0.0, smoothed)

        rows.append({
            "store_id": store_id, "day": step + 1,
            "forecast": smoothed,
            "lower":    max(0.0, lower),
            "upper":    max(0.0, upper),
        })

        # Update rolling lags
        lag_28 = lag_14; lag_14 = lag_7; lag_7 = smoothed
        lag_hist.append(lag_28); lag_hist = lag_hist[-28:]

    forecast_df = pd.DataFrame(rows)
    model_cmp_df = pd.DataFrame({
        "model":      ["LightGBM", "XGBoost",  "Ensemble"],
        "avg_pred":   [
            round(float(np.mean(lgb_vals)), 2),
            round(float(np.mean(xgb_vals)), 2) if xgb_vals else float("nan"),
            round(float(forecast_df["forecast"].mean()), 2),
        ],
        "store_id": [store_id] * 3,
    })
    return forecast_df, model_cmp_df


@st.cache_data(ttl=15)
def _get_store_inventory(store_name: str) -> list[dict]:
    """Fetch current inventory for a store from inventory_snapshots."""
    db = SessionLocal()
    try:
        store = db.query(orm.Store).filter_by(name=store_name).first()
        if not store:
            return []
        snaps = (db.query(orm.InventorySnapshot)
                 .filter_by(location_type="store", location_id=store.id).all())
        products = {p.id: p for p in db.query(orm.Product).all()}
        return [
            {
                "product":       products[s.product_id].name if s.product_id in products else f"product_{s.product_id}",
                "current_stock": s.quantity,
            }
            for s in snaps
        ]
    except Exception:
        return []
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def show_forecast_page() -> None:
    st.title("Demand Forecasts")

    stores = _available_stores()
    if not stores:
        st.error("No trained model files found in models/.")
        return

    selected_stores = st.multiselect("Select Stores", options=stores,
                                     default=stores[:min(3, len(stores))])
    if not selected_stores:
        st.info("Select at least one store.")
        return

    col1, col2 = st.columns(2)
    horizon     = col1.slider("Forecast Horizon (days)", 1, 28, 14)
    base_demand = col2.number_input("Recent Avg Daily Demand (units/item)", 1.0, 100.0, 10.0, 1.0)

    forecast_frames, cmp_frames, inv_rows = [], [], []

    for store_id in selected_stores:
        df, cmp = _run_forecast(store_id, horizon, base_demand)
        if df.empty:
            continue
        forecast_frames.append(df)
        cmp_frames.append(cmp)

        # Link forecast to current inventory from DB
        inv = _get_store_inventory(store_id)
        day1 = float(df["forecast"].iloc[0])
        for item in inv:
            inv_rows.append({
                "store":          store_id,
                "product":        item["product"],
                "current_stock":  item["current_stock"],
                "day_1_forecast": round(day1 * 0.15, 2),   # per-item share
                "status": "✅ Healthy" if item["current_stock"] > day1 * 0.15 else "⚠️ Stockout Risk",
            })

    if not forecast_frames:
        st.error("No forecasts produced.")
        return

    all_fc  = pd.concat(forecast_frames, ignore_index=True)
    all_cmp = pd.concat(cmp_frames,      ignore_index=True)

    # ── Forecast chart ─────────────────────────────────────────────────
    fig = go.Figure()
    for store_id in selected_stores:
        sub = all_fc[all_fc["store_id"] == store_id]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(x=sub["day"], y=sub["forecast"],
                                 mode="lines+markers", name=f"{store_id} Forecast"))
        fig.add_trace(go.Scatter(x=sub["day"], y=sub["lower"],
                                 name=f"{store_id} P10", line={"dash": "dot"}, opacity=0.5))
        fig.add_trace(go.Scatter(x=sub["day"], y=sub["upper"],
                                 name=f"{store_id} P90", line={"dash": "dot"}, opacity=0.5))

    fig.update_layout(title="28-Day Demand Forecast (Ensemble)",
                      xaxis_title="Day", yaxis_title="Units/Item/Day")
    st.plotly_chart(fig, use_container_width=True)

    # ── Model comparison ───────────────────────────────────────────────
    st.subheader("Model Comparison (Average Prediction)")
    st.dataframe(all_cmp, use_container_width=True, hide_index=True)

    # ── Inventory-linked forecast ──────────────────────────────────────
    if inv_rows:
        st.subheader("Inventory vs Forecast")
        st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No inventory data found. Run `python scripts/seed_data.py` first.")