from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_auth_login():
    response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
