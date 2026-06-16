from src.api.schemas import (
    PaginationParams, PaginatedResponse, ErrorDetail, APIError,
    SuccessResponse, ProductResponse, ProductListResponse,
    InventoryResponse, InventoryAlert, OrderResponse, KPISummary,
    DailyKPI, AgentStatus, AgentDecisionLog, ConfigUpdateRequest
)
from src.api.routes.forecast import ForecastRequest, ForecastResponse
from src.api.routes.simulation import SimulationStartRequest, SimulationStartResponse, SimulationStatus, SimulationMetrics, DisruptionRequest
from pydantic import ValidationError
import pytest

def test_forecast_request():
    req = ForecastRequest(features={"a": 1.0}, horizon=14, model="xgb", store="CA_2")
    assert req.horizon == 14
    assert req.model == "xgb"

    with pytest.raises(ValidationError):
        ForecastRequest(features={"a": 1.0}, horizon=0) # < 1
    with pytest.raises(ValidationError):
        ForecastRequest(features={"a": 1.0}, model="invalid")

def test_forecast_response():
    resp = ForecastResponse(model="xgb", forecast=[1.0], lower=[0.5], upper=[1.5])
    assert resp.model == "xgb"

def test_simulation_start_request():
    req = SimulationStartRequest(days=30)
    assert req.days == 30
    with pytest.raises(ValidationError):
        SimulationStartRequest(days=400) # > 365

def test_simulation_start_response():
    resp = SimulationStartResponse(simulation_id="abc", status="started", days=30)
    assert resp.simulation_id == "abc"

def test_simulation_status():
    status = SimulationStatus(running=True)
    assert status.running is True

def test_simulation_metrics():
    metrics = SimulationMetrics(total_revenue=100.0, total_profit=50.0, fill_rate=0.9, stockout_rate=0.1, on_time_delivery_rate=0.95)
    assert metrics.total_revenue == 100.0

def test_disruption_request():
    req = DisruptionRequest(type="supplier_delay")
    assert req.severity == "medium"
    assert req.params == {}

def test_pagination_params():
    params = PaginationParams()
    assert params.page == 1
    assert params.page_size == 20

def test_api_error():
    err = APIError(detail="error")
    assert err.detail == "error"

def test_success_response():
    succ = SuccessResponse(message="ok")
    assert succ.message == "ok"

def test_product_list_response():
    resp = ProductListResponse(total=1, page=1, page_size=20, total_pages=1, items=[
        ProductResponse(product_id=1, product_name="A", category_id=1, unit_cost=1.0, base_price=2.0, is_perishable=False)
    ])
    assert resp.total == 1

def test_agent_decision_log():
    log = AgentDecisionLog(agent_name="agent", action="buy", details="test", success=True)
    assert log.success is True

def test_config_update_request():
    req = ConfigUpdateRequest(values={"key": "val"})
    assert req.section == "simulation"
