from __future__ import annotations

from src.api.auth import authenticate_user, create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hashing():
    hashed = get_password_hash("secret")
    assert verify_password("secret", hashed)


def test_authenticate_user():
    assert authenticate_user("admin", "admin123") is not None


def test_token_round_trip():
    token = create_access_token({"sub": "admin", "role": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
