"""Inventory monitoring page — reads from inventory_snapshots (real table name)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.database import SessionLocal
from src.core import models as orm


@st.cache_data(ttl=15)
def _fetch_inventory(store_filter: str = "All") -> pd.DataFrame:
    """Pull from inventory_snapshots joined to products and stores."""
    db = SessionLocal()
    try:
        snaps    = db.query(orm.InventorySnapshot).filter_by(location_type="store").all()
        products = {p.id: p for p in db.query(orm.Product).all()}
        stores   = {s.id: s for s in db.query(orm.Store).all()}

        if not snaps:
            return pd.DataFrame()

        rows = []
        for s in snaps:
            prod  = products.get(s.product_id)
            store = stores.get(s.location_id)
            if store_filter != "All" and (store is None or store.name != store_filter):
                continue
            rows.append({
                "store":      store.name     if store else f"store_{s.location_id}",
                "region":     store.region   if store else "unknown",
                "product":    prod.name      if prod  else f"product_{s.product_id}",
                "category":   prod.category  if prod  else "unknown",
                "unit_cost":  prod.unit_cost if prod  else 0.0,
                "base_price": prod.base_price if prod else 0.0,
                "stock_level": s.quantity,
                "updated_at": s.updated_at,
            })
        return pd.DataFrame(rows)
    except Exception as exc:
        st.error(f"Database error: {exc}")
        return pd.DataFrame()
    finally:
        db.close()


@st.cache_data(ttl=60)
def _fetch_store_names() -> list[str]:
    db = SessionLocal()
    try:
        stores = db.query(orm.Store).order_by(orm.Store.id).all()
        return [s.name for s in stores]
    except Exception:
        return []
    finally:
        db.close()


def _status_label(stock: int) -> str:
    if stock == 0:      return "🔴 Out of stock"
    if stock < 50:      return "🟡 Low stock"
    return "🟢 OK"


def _color_status(val: str) -> str:
    if "Out"  in val: return "background-color:#ffd6d6; color:#a32d2d"
    if "Low"  in val: return "background-color:#fff4d6; color:#854f0b"
    return "background-color:#eaf3de; color:#3b6d11"


def show_inventory_page() -> None:
    st.title("Inventory Monitor")

    store_names = _fetch_store_names()
    if not store_names:
        st.error("No stores in database. Run: `python scripts/seed_data.py`")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        store_filter = st.selectbox("Filter by store", ["All"] + store_names)
    with col2:
        if st.button("🔃 Refresh"):
            st.cache_data.clear()
            st.rerun()

    df = _fetch_inventory(store_filter)

    if df.empty:
        st.warning("No inventory data found. Start a simulation to populate inventory levels.")
        return

    # ── Summary metrics ────────────────────────────────────────────────
    total_units   = int(df["stock_level"].sum())
    low_stock     = int((df["stock_level"] < 50).sum())
    out_of_stock  = int((df["stock_level"] == 0).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Units in Stock", f"{total_units:,}")
    c2.metric("Low Stock (<50 units)", low_stock)
    c3.metric("Out of Stock", out_of_stock)

    st.divider()

    # ── Inventory table with colour coding ─────────────────────────────
    st.subheader("Current Stock Levels")
    df["status"] = df["stock_level"].apply(_status_label)

    status_filter = st.multiselect(
        "Show status",
        options=["🟢 OK", "🟡 Low stock", "🔴 Out of stock"],
        default=["🟡 Low stock", "🔴 Out of stock"],
    )
    display = df[df["status"].isin(status_filter)] if status_filter else df

    styled = (
        display[["store", "category", "product", "stock_level", "status"]]
        .style.map(_color_status, subset=["status"])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Alerts ──────────────────────────────────────────────────────────
    alerts = df[df["stock_level"] < 50].sort_values("stock_level")
    if not alerts.empty:
        st.subheader(f"⚠️ {len(alerts)} items need attention")
        st.dataframe(
            alerts[["store", "product", "stock_level", "status"]],
            use_container_width=True, hide_index=True,
        )

    # ── Stock by category chart ─────────────────────────────────────────
    st.subheader("Stock by Category")
    cat_stock = df.groupby("category")["stock_level"].sum().reset_index()
    fig = px.bar(cat_stock, x="category", y="stock_level",
                 color="category", title="Total Stock by Category")
    st.plotly_chart(fig, use_container_width=True)