#!/usr/bin/env python3
"""Seed the database with real M5-aligned data using the CORRECT schema.

Real schema (from ORM models.py):
  stores:             id INTEGER, name VARCHAR, region VARCHAR
  products:           id INTEGER, name VARCHAR, category VARCHAR,
                      unit_cost FLOAT, base_price FLOAT, shelf_life_days INTEGER
  inventory_snapshots: id INTEGER, product_id INTEGER, location_type VARCHAR,
                       location_id INTEGER, quantity INTEGER, updated_at DATETIME
  suppliers:          id INTEGER, name VARCHAR, reliability_score FLOAT
  warehouses:         id INTEGER, name VARCHAR, warehouse_type VARCHAR
  supplier_products:  id INTEGER, supplier_id INTEGER, product_id INTEGER

Usage:
    python scripts/seed_data.py            # full seed
    python scripts/seed_data.py --minimal  # 1 store, 3 products
    python scripts/seed_data.py --clear    # wipe rows then re-seed
"""

from __future__ import annotations

import argparse

from src.core.database import SessionLocal, init_db
from src.core import models as m

# ---------------------------------------------------------------------------
# Seed data — INTEGER ids, correct column names, aligned to M5 store names
# ---------------------------------------------------------------------------

M5_STORES = [
    {"id": 1,  "name": "CA_1", "region": "California"},
    {"id": 2,  "name": "CA_2", "region": "California"},
    {"id": 3,  "name": "CA_3", "region": "California"},
    {"id": 4,  "name": "CA_4", "region": "California"},
    {"id": 5,  "name": "TX_1", "region": "Texas"},
    {"id": 6,  "name": "TX_2", "region": "Texas"},
    {"id": 7,  "name": "TX_3", "region": "Texas"},
    {"id": 8,  "name": "WI_1", "region": "Wisconsin"},
    {"id": 9,  "name": "WI_2", "region": "Wisconsin"},
    {"id": 10, "name": "WI_3", "region": "Wisconsin"},
]

# unit_cost + base_price (NOT unit_price — that column does not exist)
M5_PRODUCTS = [
    {"id": 1,  "name": "FOODS_3_001",    "category": "FOODS",     "unit_cost": 1.20, "base_price": 2.98,  "shelf_life_days": 7},
    {"id": 2,  "name": "FOODS_3_002",    "category": "FOODS",     "unit_cost": 0.85, "base_price": 1.99,  "shelf_life_days": 5},
    {"id": 3,  "name": "FOODS_3_003",    "category": "FOODS",     "unit_cost": 1.50, "base_price": 3.49,  "shelf_life_days": 14},
    {"id": 4,  "name": "FOODS_2_001",    "category": "FOODS",     "unit_cost": 2.10, "base_price": 4.99,  "shelf_life_days": 30},
    {"id": 5,  "name": "FOODS_1_001",    "category": "FOODS",     "unit_cost": 0.60, "base_price": 1.49,  "shelf_life_days": 90},
    {"id": 6,  "name": "HOBBIES_1_001",  "category": "HOBBIES",   "unit_cost": 3.50, "base_price": 7.99,  "shelf_life_days": 0},
    {"id": 7,  "name": "HOBBIES_1_002",  "category": "HOBBIES",   "unit_cost": 5.00, "base_price": 11.99, "shelf_life_days": 0},
    {"id": 8,  "name": "HOUSEHOLD_1_001","category": "HOUSEHOLD", "unit_cost": 1.80, "base_price": 4.49,  "shelf_life_days": 0},
    {"id": 9,  "name": "HOUSEHOLD_1_002","category": "HOUSEHOLD", "unit_cost": 2.20, "base_price": 5.99,  "shelf_life_days": 0},
    {"id": 10, "name": "HOUSEHOLD_2_001","category": "HOUSEHOLD", "unit_cost": 3.00, "base_price": 6.99,  "shelf_life_days": 0},
]

M5_WAREHOUSES = [
    {"id": 1, "name": "CA_DC",     "warehouse_type": "distribution_center"},
    {"id": 2, "name": "TX_DC",     "warehouse_type": "distribution_center"},
    {"id": 3, "name": "WI_DC",     "warehouse_type": "distribution_center"},
    {"id": 4, "name": "CENTRAL_DC","warehouse_type": "central_hub"},
]

M5_SUPPLIERS = [
    {"id": 1, "name": "Grocery Supplier",          "reliability_score": 0.97},
    {"id": 2, "name": "Hobbies & Toys Distributor","reliability_score": 0.92},
    {"id": 3, "name": "Household Goods Co.",        "reliability_score": 0.95},
]

# supplier_id → product_ids
SUPPLIER_PRODUCTS = (
    [(1, pid) for pid in range(1, 6)] +   # grocery covers FOODS
    [(2, pid) for pid in range(6, 8)] +   # hobbies
    [(3, pid) for pid in range(8, 11)]    # household
)

# Starting inventory: 100 units of every product in every store
# Uses inventory_snapshots with location_type="store", location_id=store.id
INITIAL_STOCK = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear(db) -> None:
    for cls in [m.SupplierProduct, m.KPISnapshot, m.AgentDecision,
                m.InventorySnapshot, m.Order, m.ExternalFactor,
                m.Supplier, m.Warehouse, m.Product, m.Store]:
        db.query(cls).delete()
    db.commit()
    print("All rows cleared.")


def _seed_full(db) -> None:
    for row in M5_STORES:
        if not db.get(m.Store, row["id"]):
            db.add(m.Store(**row))
    db.flush()

    for row in M5_PRODUCTS:
        if not db.get(m.Product, row["id"]):
            db.add(m.Product(**row))
    db.flush()

    for row in M5_WAREHOUSES:
        if not db.get(m.Warehouse, row["id"]):
            db.add(m.Warehouse(**row))

    for row in M5_SUPPLIERS:
        if not db.get(m.Supplier, row["id"]):
            db.add(m.Supplier(**row))
    db.flush()

    for sup_id, prod_id in SUPPLIER_PRODUCTS:
        exists = (db.query(m.SupplierProduct)
                  .filter_by(supplier_id=sup_id, product_id=prod_id).first())
        if not exists:
            db.add(m.SupplierProduct(supplier_id=sup_id, product_id=prod_id))

    # Seed starting inventory in inventory_snapshots
    # location_type="store", location_id=store integer id
    for store in M5_STORES:
        for product in M5_PRODUCTS:
            exists = (db.query(m.InventorySnapshot)
                      .filter_by(location_type="store",
                                 location_id=store["id"],
                                 product_id=product["id"]).first())
            if not exists:
                db.add(m.InventorySnapshot(
                    product_id=product["id"],
                    location_type="store",
                    location_id=store["id"],
                    quantity=INITIAL_STOCK,
                ))

    db.commit()
    print(f"Seeded: {len(M5_STORES)} stores, {len(M5_PRODUCTS)} products, "
          f"{len(M5_WAREHOUSES)} warehouses, {len(M5_SUPPLIERS)} suppliers, "
          f"{len(M5_STORES) * len(M5_PRODUCTS)} inventory rows.")


def _seed_minimal(db) -> None:
    """1 store (CA_1), first 3 products only."""
    store = M5_STORES[0]
    if not db.get(m.Store, store["id"]):
        db.add(m.Store(**store))
    db.flush()
    for row in M5_PRODUCTS[:3]:
        if not db.get(m.Product, row["id"]):
            db.add(m.Product(**row))
    db.flush()
    for product in M5_PRODUCTS[:3]:
        exists = (db.query(m.InventorySnapshot)
                  .filter_by(location_type="store",
                             location_id=store["id"],
                             product_id=product["id"]).first())
        if not exists:
            db.add(m.InventorySnapshot(
                product_id=product["id"],
                location_type="store",
                location_id=store["id"],
                quantity=INITIAL_STOCK,
            ))
    db.commit()
    print("Minimal seed: 1 store, 3 products, 3 inventory rows.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def seed_all(clear_first: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if clear_first:
            _clear(db)
        _seed_full(db)
    finally:
        db.close()


def seed_minimal() -> None:
    init_db()
    db = SessionLocal()
    try:
        _seed_minimal(db)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimal", action="store_true")
    parser.add_argument("--clear",   action="store_true")
    args = parser.parse_args()
    if args.minimal:
        seed_minimal()
    else:
        seed_all(clear_first=args.clear)