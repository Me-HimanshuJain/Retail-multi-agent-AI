

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_auth_login():
    response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    # P1: login response now includes refresh_token and expires_in
    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_in" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"
    assert data["role"] == "admin"
