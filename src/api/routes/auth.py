"""Authentication routes.

Token lifecycle (P1)
---------------------
POST /auth/token
    Issues a short-lived JWT access token (30 min default) PLUS a long-lived
    opaque refresh token (7 days default).  The refresh token is stored in the
    RefreshTokenStore (Redis-first, in-process fallback).
    Rate limited to 5 requests/minute per IP (brute-force mitigation).

POST /auth/refresh
    Accepts the opaque refresh token in the request body.  Validates, *consumes*
    (single-use), and issues a new access + refresh token pair (rotation).
    A second call with the same refresh token returns 401.

GET /auth/me
    Returns the current user from the JWT access token.

Rate limiting note
------------------
slowapi's @limiter.limit decorator breaks FastAPI's Depends() introspection when
stacked above @router.post.  The correct order is router.post first, then the
limiter, which is achieved by applying @limiter.limit on a wrapper that calls
the actual handler — see the `_rate_limited_login` pattern below.
"""

import functools
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from pydantic import BaseModel
from src.api.limiter import limiter

from src.api import refresh_store
from src.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    User,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int                 # seconds until access token expires
    username: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    username: str
    role: str
    is_active: bool


# ---------------------------------------------------------------------------
# Shared login logic (extracted so the rate-limited wrapper stays thin)
# ---------------------------------------------------------------------------

async def _do_login(username: str, password: str) -> LoginResponse:
    """Core login logic — validate credentials and issue token pair."""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        {"sub": user.username, "role": user.role},
        expires,
    )
    rt = refresh_store.issue(
        username=user.username,
        role=user.role,
        ttl_seconds=settings.REFRESH_TOKEN_TTL_SECONDS,
    )
    return LoginResponse(
        access_token=access_token,
        refresh_token=rt,
        expires_in=int(expires.total_seconds()),
        username=user.username,
        role=user.role,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/token", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> LoginResponse:
    """Authenticate with username + password; receive access + refresh tokens."""
    return await _do_login(form_data.username, form_data.password)


@router.get("/me", response_model=UserInfo)
async def read_users_me(current_user: User = Depends(get_current_user)) -> UserInfo:
    """Return the identity of the currently authenticated user."""
    return UserInfo(**current_user.model_dump())


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(body: RefreshRequest) -> LoginResponse:
    """Exchange a valid refresh token for a new access + refresh token pair.

    The submitted refresh token is consumed (single-use): a second call with
    the same token returns 401.  This rotation pattern limits the window of
    exposure if a refresh token is stolen.
    """
    payload = refresh_store.consume(body.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or has already been used.",
        )
    username = payload["username"]
    role = payload["role"]

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access = create_access_token({"sub": username, "role": role}, expires)
    new_refresh = refresh_store.issue(
        username=username,
        role=role,
        ttl_seconds=settings.REFRESH_TOKEN_TTL_SECONDS,
    )
    return LoginResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=int(expires.total_seconds()),
        username=username,
        role=role,
    )
