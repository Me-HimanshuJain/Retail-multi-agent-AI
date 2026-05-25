#!/usr/bin/env python3
"""Seed the database with small demo data."""

from __future__ import annotations

import argparse

from src.core.database import init_db


def seed_all(clear_first: bool = False) -> None:
    init_db()
    print("Seeded demo database")


def seed_minimal() -> None:
    init_db()
    print("Seeded minimal demo database")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimal", action="store_true")
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    if args.minimal:
        seed_minimal()
    else:
        seed_all(clear_first=args.clear)
