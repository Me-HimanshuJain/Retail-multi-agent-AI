"""P1 security tests — rate limiting, CORS, error handling, token TTL, refresh tokens."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api import refresh_store

client = TestClient(app, raise_server_exceptions=False)

import uuid
import pytest

@pytest.fixture(autouse=True)
def isolate_rate_limits():
    """Give each test a unique IP so the rate limiter state doesn't bleed."""
    client.headers["x-forwarded-for"] = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(username: str = "admin", password: str = "admin123") -> dict:
    resp = client.post("/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Rate limiting — POST /auth/token (5/minute limit)
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_login_rate_limit_fires_on_6th_request(self):
        """Test the 5 per minute rate limit on POST /auth/token."""
        # 5 successful requests
        for _ in range(5):
            resp = client.post("/auth/token", data={"username": "admin", "password": "wrongpassword"})
            assert resp.status_code == 401

        # 6th request fails with 429
        resp = client.post("/auth/token", data={"username": "admin", "password": "wrongpassword"})
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["error"]

    def test_predict_accepts_authenticated_request(self):
        """Authenticated predict calls should return 200 or 404 (not 429 on first call)."""
        token = _login("viewer", "viewer123")["access_token"]
        resp = client.post(
            "/forecast/predict",
            json={"features": {}, "store": "CA_1"},
            headers=_auth_header(token),
        )
        assert resp.status_code in {200, 404}, f"Unexpected {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 2. CORS — allowlist enforcement
# ---------------------------------------------------------------------------

class TestCORSAllowlist:
    def test_allowed_origin_receives_cors_header(self):
        """Requests from the Streamlit default origin get the correct CORS header."""
        resp = client.get("/health", headers={"Origin": "http://localhost:8501"})
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:8501"

    def test_disallowed_origin_does_not_reflect_in_cors_header(self):
        """Unknown origins must not appear in the allow-origin header."""
        resp = client.get("/health", headers={"Origin": "http://evil.example.com"})
        acao = resp.headers.get("access-control-allow-origin", "")
        assert "evil.example.com" not in acao

    def test_wildcard_not_used_as_cors_header(self):
        """The wildcard must never appear — P1 requirement."""
        resp = client.get("/health", headers={"Origin": "http://localhost:8501"})
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao != "*", "Wildcard CORS must not be used"


# ---------------------------------------------------------------------------
# 3. Secure error responses
# ---------------------------------------------------------------------------

class TestSecureErrorResponses:
    def test_invalid_refresh_token_returns_clean_401(self):
        """Bad refresh tokens must return clean 401 without internal details."""
        resp = client.post("/auth/refresh", json={"refresh_token": "bad-token"})
        assert resp.status_code == 401
        body = resp.json()
        assert "traceback" not in str(body).lower()
        assert "file " not in str(body).lower()
        assert set(body.keys()) == {"detail"}

    def test_wrong_password_returns_clean_401(self):
        """Failed login must return {detail: str} only."""
        resp = client.post("/auth/token", data={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401
        body = resp.json()
        assert isinstance(body.get("detail"), str)
        assert "traceback" not in str(body).lower()


# ---------------------------------------------------------------------------
# 4. Short-lived access tokens
# ---------------------------------------------------------------------------

class TestAccessTokenTTL:
    def test_login_response_includes_expires_in(self):
        """Login response must include expires_in (seconds)."""
        data = _login()
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_expires_in_matches_jwt_expiration_minutes(self):
        """expires_in should equal JWT_EXPIRATION_MINUTES * 60."""
        from src.core.config import settings
        data = _login()
        expected = settings.JWT_EXPIRATION_MINUTES * 60
        assert abs(data["expires_in"] - expected) <= 5

    def test_jwt_expiration_minutes_is_short(self):
        """JWT_EXPIRATION_MINUTES must be <=60 for P1 compliance."""
        from src.core.config import settings
        assert settings.JWT_EXPIRATION_MINUTES <= 60, (
            f"JWT_EXPIRATION_MINUTES={settings.JWT_EXPIRATION_MINUTES} exceeds 60 min limit"
        )


# ---------------------------------------------------------------------------
# 5. Refresh tokens — opaque, single-use, rotating
# ---------------------------------------------------------------------------

class TestRefreshTokens:
    def test_login_issues_both_tokens(self):
        """Login returns both access_token and refresh_token."""
        data = _login()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != data["access_token"]

    def test_refresh_token_is_opaque_not_jwt(self):
        """Refresh token must not be a JWT (no two '.' separators)."""
        data = _login()
        rt = data["refresh_token"]
        assert rt.count(".") != 2, "Refresh token must not be a JWT"

    def test_refresh_issues_new_token_pair(self):
        """POST /auth/refresh returns new access + refresh tokens."""
        data = _login()
        original_rt = data["refresh_token"]

        resp = client.post("/auth/refresh", json={"refresh_token": original_rt})
        assert resp.status_code == 200, f"Refresh failed: {resp.text}"
        new_data = resp.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["refresh_token"] != original_rt

    def test_refresh_token_single_use_enforced(self):
        """Same refresh token used twice must fail on the second attempt."""
        data = _login()
        rt = data["refresh_token"]

        resp1 = client.post("/auth/refresh", json={"refresh_token": rt})
        assert resp1.status_code == 200, f"First refresh failed: {resp1.text}"

        resp2 = client.post("/auth/refresh", json={"refresh_token": rt})
        assert resp2.status_code == 401, (
            f"Expected 401 on reuse, got {resp2.status_code}: {resp2.text}"
        )

    def test_invalid_refresh_token_returns_401(self):
        """Random string as refresh token returns 401, not 500."""
        resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
        assert resp.status_code == 401

    def test_refresh_store_unit_issue_and_consume(self):
        """Unit: issue → consume returns payload; second consume returns None."""
        token = refresh_store.issue("testuser", "viewer", ttl_seconds=300)
        assert isinstance(token, str) and len(token) > 16

        payload = refresh_store.consume(token)
        assert payload == {"username": "testuser", "role": "viewer"}

        payload2 = refresh_store.consume(token)
        assert payload2 is None

    def test_refresh_store_unit_expired_returns_none(self):
        """Tokens with TTL=0 are immediately expired."""
        token = refresh_store.issue("expireduser", "viewer", ttl_seconds=0)
        time.sleep(0.05)
        payload = refresh_store.consume(token)
        assert payload is None

    def test_refresh_store_unit_revoke(self):
        """Revoked tokens cannot be consumed."""
        token = refresh_store.issue("revokeuser", "admin", ttl_seconds=300)
        refresh_store.revoke(token)
        assert refresh_store.consume(token) is None
