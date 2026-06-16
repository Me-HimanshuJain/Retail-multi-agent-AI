"""Opaque refresh token store — Redis-first, in-process fallback.

Design
------
Refresh tokens are random opaque strings (not JWTs).  They cannot be decoded
or forged without access to the store.  Each token maps to a payload
``{username, role}`` with a TTL.

Modes
-----
Redis mode (preferred)
    When ``REDIS_HOST`` resolves and a connection is established on startup,
    tokens are stored as ``refresh:{token}`` keys with native ``SETEX`` TTL.
    Tokens survive API restarts and are shared across all instances.

In-process fallback
    When Redis is not available, tokens are stored in a module-level ``dict``
    with a manually checked expiry timestamp.  Suitable for single-instance
    dev/CI.  Tokens are lost on restart.

Single-use enforcement
----------------------------------------------
``consume()`` atomically reads and deletes the token.  A second call with the
same token always returns ``None``, even in the Redis pipeline implementation.
This prevents replay attacks with stolen refresh tokens.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process fallback store
# ---------------------------------------------------------------------------
_store: dict[str, dict] = {}   # {token: {username, role, exp}}


def _now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# Redis connection (optional)
# ---------------------------------------------------------------------------
_redis_client = None


def _get_redis():
    """Return a Redis client, or None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from src.core.config import settings
        import redis

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=1,               # separate DB from event bus (DB 0)
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()           # validate connectivity
        _redis_client = client
        logger.info("RefreshTokenStore: using Redis at %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as exc:
        logger.warning("RefreshTokenStore: Redis unavailable (%s), using in-process fallback", exc)
        _redis_client = None
    return _redis_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def issue(username: str, role: str, ttl_seconds: int) -> str:
    """Generate a new opaque refresh token and persist it.

    Parameters
    ----------
    username:
        The authenticated user's username.
    role:
        The authenticated user's role.
    ttl_seconds:
        How long (in seconds) the token should remain valid.

    Returns
    -------
    str
        The opaque token string.  Never a JWT.
    """
    token = secrets.token_urlsafe(32)
    payload = json.dumps({"username": username, "role": role})

    r = _get_redis()
    if r is not None:
        try:
            r.setex(f"refresh:{token}", ttl_seconds, payload)
            return token
        except Exception as exc:
            logger.warning("RefreshTokenStore: Redis write failed (%s), falling back", exc)

    # In-process fallback
    _store[token] = {
        "username": username,
        "role": role,
        "exp": _now() + ttl_seconds,
    }
    return token


def consume(token: str) -> Optional[dict]:
    """Validate, consume (delete), and return the token payload.

    This is a single-use operation: the token is deleted immediately after
    being read, regardless of whether the caller uses the returned payload.

    Parameters
    ----------
    token:
        The opaque refresh token string.

    Returns
    -------
    dict or None
        ``{username: str, role: str}`` if valid, ``None`` if invalid/expired.
    """
    r = _get_redis()
    if r is not None:
        try:
            key = f"refresh:{token}"
            # Atomic get-and-delete using a pipeline
            pipe = r.pipeline()
            pipe.get(key)
            pipe.delete(key)
            results = pipe.execute()
            raw = results[0]
            if not raw:
                return None
            data = json.loads(raw)
            return {"username": data["username"], "role": data["role"]}
        except Exception as exc:
            logger.warning("RefreshTokenStore: Redis read failed (%s), falling back", exc)

    # In-process fallback
    entry = _store.pop(token, None)
    if entry is None:
        return None
    if _now() > entry["exp"]:
        return None     # expired (already popped)
    return {"username": entry["username"], "role": entry["role"]}


def revoke(token: str) -> None:
    """Explicitly invalidate a refresh token (e.g., on logout).

    Parameters
    ----------
    token:
        The opaque refresh token string to invalidate.
    """
    r = _get_redis()
    if r is not None:
        try:
            r.delete(f"refresh:{token}")
            return
        except Exception as exc:
            logger.warning("RefreshTokenStore: Redis delete failed (%s), falling back", exc)

    _store.pop(token, None)
