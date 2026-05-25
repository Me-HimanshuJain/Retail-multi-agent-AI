from __future__ import annotations

from src.core.database import Base, engine, init_db


def test_init_db():
    init_db()
    assert Base.metadata.tables
