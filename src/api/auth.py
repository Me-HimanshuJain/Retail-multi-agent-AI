"""JWT authentication helpers.

Password hashing
----------------
Uses the ``bcrypt`` library directly — a proper key derivation function with
per-hash salts and a configurable work factor (~100 ms/hash at rounds=12,
making brute-force infeasible even with GPU cracking rigs).

SHA-256 was the previous implementation.  It is NOT a KDF (no salt, no work
factor, ~25 billion ops/sec on a GPU) and must never be used for password
storage.

Bootstrap users
---------------
Users are loaded from the ``BOOTSTRAP_USERS_JSON`` environment variable — a
JSON array of objects with ``username``, ``role``, and ``hashed_password``
(a bcrypt hash string, never the plaintext).  This keeps credentials out of
source code while remaining zero-config for CI (``conftest.py`` seeds the env
var before any import).

Generate a bcrypt hash for a password::

    python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt(rounds=12)).decode())"
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings

# ---------------------------------------------------------------------------
# JWT config
# ---------------------------------------------------------------------------
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRATION_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ---------------------------------------------------------------------------
# Password hashing — bcrypt (direct, no passlib wrapper)
# ---------------------------------------------------------------------------

def get_password_hash(password: str, rounds: int = 12) -> str:
    """Return a bcrypt hash of *password*.

    Parameters
    ----------
    password : str
        The plaintext password to hash.
    rounds : int
        bcrypt work factor (log2 of iterations).  Production default is 12
        (~100 ms/hash).  Use 4 in tests for speed.

    Returns
    -------
    str
        A bcrypt hash string starting with ``$2b$``.
    """
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------

class User(BaseModel):
    username: str
    role: str
    is_active: bool = True


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# Bootstrap user store — loaded from BOOTSTRAP_USERS_JSON env var
# ---------------------------------------------------------------------------

def _load_bootstrap_users() -> Dict[str, UserInDB]:
    """Load users from the BOOTSTRAP_USERS_JSON environment variable.

    Expected format::

        [
            {"username": "admin", "role": "admin", "hashed_password": "$2b$12$..."},
            {"username": "viewer", "role": "viewer", "hashed_password": "$2b$12$..."}
        ]

    Returns an empty dict (no users) if the env var is absent or blank.

    Raises
    ------
    ValueError
        If the env var is set but is not valid JSON.
    """
    raw = os.getenv("BOOTSTRAP_USERS_JSON", "").strip()
    if not raw:
        return {}
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"BOOTSTRAP_USERS_JSON is not valid JSON: {exc}. "
            "Set it to a JSON array of {username, role, hashed_password} objects."
        ) from exc

    return {
        entry["username"]: UserInDB(
            username=entry["username"],
            role=entry["role"],
            hashed_password=entry["hashed_password"],
            is_active=entry.get("is_active", True),
        )
        for entry in entries
    }


USERS_DB: Dict[str, UserInDB] = _load_bootstrap_users()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_user(username: str) -> Optional[UserInDB]:
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: Optional[str] = payload.get("sub") or payload.get("username")
    role: str = payload.get("role", "viewer")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(username=user.username, role=role, is_active=user.is_active)


class RoleChecker:
    """FastAPI dependency that enforces role-based access control."""

    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = set(allowed_roles)

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role}' is not permitted for this endpoint. "
                    f"Required: {sorted(self.allowed_roles)}"
                ),
            )
        return current_user


admin_required    = RoleChecker(["admin"])
operator_required = RoleChecker(["admin", "operator"])
any_authenticated = RoleChecker(["admin", "operator", "viewer"])
