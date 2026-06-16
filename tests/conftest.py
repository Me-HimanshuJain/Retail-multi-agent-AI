"""Pytest configuration — seeds required environment variables before any app import.

IMPORTANT: This file must set SECRET_KEY and BOOTSTRAP_USERS_JSON BEFORE any
src.* import occurs.  pytest loads conftest.py first, so placing os.environ
assignments here guarantees Settings.__post_init__ sees a valid SECRET_KEY and
authenticate_user() finds bootstrap users during all test runs.

Bcrypt rounds=4 (vs production default 12) keeps each hash at ~4 ms instead
of ~100 ms, so the three test user hashes add only ~12 ms to the suite startup.
"""

from __future__ import annotations

import json
import os
import secrets

# ---------------------------------------------------------------------------
# Bootstrap SECRET_KEY before any src.* import
# ---------------------------------------------------------------------------
os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))

# ---------------------------------------------------------------------------
# Bootstrap test users with bcrypt hashes (fast rounds for CI)
# ---------------------------------------------------------------------------
import bcrypt  # noqa: E402

def _hash(password: str, rounds: int = 4) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)).decode()

_TEST_USERS = [
    {"username": "admin",    "role": "admin",    "hashed_password": _hash("admin123")},
    {"username": "operator", "role": "operator", "hashed_password": _hash("operator123")},
    {"username": "viewer",   "role": "viewer",   "hashed_password": _hash("viewer123")},
]

os.environ.setdefault("BOOTSTRAP_USERS_JSON", json.dumps(_TEST_USERS))


