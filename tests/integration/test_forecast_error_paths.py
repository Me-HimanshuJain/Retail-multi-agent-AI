from fastapi.testclient import TestClient
import pytest
from src.api.main import app

client = TestClient(app)

from src.api.limiter import limiter

@pytest.fixture(autouse=True)
def isolate_rate_limits():
    limiter.reset()

def _get_token(username: str, password: str) -> str:
    resp = client.post("/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers():
    token = _get_token("viewer", "viewer123")
    return _auth_header(token)

def test_forecast_predict_404_missing_xgb_artifact(auth_headers):
    # Store that doesn't have an XGB model artifact
    response = client.post(
        "/forecast/predict",
        headers=auth_headers,
        json={"features": {}, "horizon": 1, "model": "xgb", "store": "MISSING_STORE"}
    )
    assert response.status_code == 404
    assert "not available for the given store" in response.json()["detail"].lower()

def test_forecast_predict_404_missing_lgbm_artifact(auth_headers):
    # Store that doesn't have an LGBM model artifact
    response = client.post(
        "/forecast/predict",
        headers=auth_headers,
        json={"features": {}, "horizon": 1, "model": "lgbm", "store": "MISSING_STORE"}
    )
    assert response.status_code == 404
    assert "not available for the given store" in response.json()["detail"].lower()

def test_forecast_predict_404_missing_ensemble_artifact(auth_headers):
    # Store that doesn't have an ensemble artifact
    response = client.post(
        "/forecast/predict",
        headers=auth_headers,
        json={"features": {}, "horizon": 1, "model": "ensemble", "store": "MISSING_STORE"}
    )
    assert response.status_code == 404
    assert "artifact not found" in response.json()["detail"].lower()

def test_forecast_predict_invalid_model_type(auth_headers):
    # Invalid model string
    response = client.post(
        "/forecast/predict",
        headers=auth_headers,
        json={"features": {}, "horizon": 1, "model": "invalid_model_xyz", "store": "CA_1"}
    )
    assert response.status_code == 422
    assert "should match pattern" in response.json()["detail"][0]["msg"].lower()

def test_forecast_predict_invalid_horizon_high(auth_headers):
    # Horizon too high
    response = client.post(
        "/forecast/predict",
        headers=auth_headers,
        json={"features": {}, "horizon": 999, "model": "xgb", "store": "CA_1"}
    )
    assert response.status_code == 422
    assert "input should be less than or equal to 28" in response.json()["detail"][0]["msg"].lower()

def test_forecast_predict_invalid_horizon_low(auth_headers):
    # Horizon too low
    response = client.post(
        "/forecast/predict",
        headers=auth_headers,
        json={"features": {}, "horizon": 0, "model": "xgb", "store": "CA_1"}
    )
    assert response.status_code == 422
    assert "input should be greater than or equal to 1" in response.json()["detail"][0]["msg"].lower()
