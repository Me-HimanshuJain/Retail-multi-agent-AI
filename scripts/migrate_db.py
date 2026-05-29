#!/usr/bin/env python3
"""One-time migration: rebuild the database schema to match the current ORM models.

Run this when you see errors like:
  'no such column: products.unit_cost'
  'no such table: inventory_snapshots'

It drops ALL tables and recreates them cleanly, then re-seeds data.
All previous simulation data will be lost (that's fine at this stage).

Usage:
    PYTHONPATH=. python scripts/migrate_db.py
"""

from __future__ import annotations

from sqlalchemy import text
from src.core.database import engine, Base, SessionLocal
from src.core import models  # noqa — registers all ORM models with Base


def migrate() -> None:
    print("Step 1: Dropping all existing tables...")
    # Drop in reverse dependency order to avoid FK errors
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))  # SQLite only
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DROP TABLE IF EXISTS {table.name}"))
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()
    print("  All tables dropped.")

    print("Step 2: Recreating tables from ORM models...")
    Base.metadata.create_all(bind=engine)
    print("  Tables created:")
    from sqlalchemy import inspect
    inspector = inspect(engine)
    for table in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns(table)]
        print(f"    {table}: {cols}")

    print("Step 3: Seeding data...")
    # Import here so seed runs after tables exist
    from scripts.seed_data import seed_all
    seed_all(clear_first=False)   # tables are already empty

    print("\nMigration complete. You can now start the API and run a simulation.")


if __name__ == "__main__":
    migrate()
