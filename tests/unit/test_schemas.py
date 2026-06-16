import pytest
from pydantic import ValidationError
from src.api.schemas import (
    PaginationParams, PaginatedResponse, ErrorDetail, APIError,
    SuccessResponse, ProductResponse, ProductListResponse,
    InventoryResponse, InventoryAlert, OrderResponse, KPISummary,
    DailyKPI, AgentStatus, AgentDecisionLog, ConfigUpdateRequest
)

def test_pagination_params():
    p = PaginationParams(page=2, page_size=50)
    assert p.page == 2
    assert p.page_size == 50
    
    with pytest.raises(ValidationError):
        PaginationParams(page=0)
        
    with pytest.raises(ValidationError):
        PaginationParams(page_size=200)

def test_paginated_response():
    r = PaginatedResponse(total=100, page=1, page_size=20, total_pages=5)
    assert r.total == 100

def test_error_detail():
    e = ErrorDetail(message="msg")
    assert e.message == "msg"
    assert e.field is None

def test_api_error():
    e = APIError(detail="error")
    assert e.detail == "error"

def test_success_response():
    s = SuccessResponse(message="ok")
    assert s.message == "ok"

def test_product_response():
    p = ProductResponse(
        product_id=1, product_name="A", category_id=2, 
        unit_cost=1.0, base_price=2.0, is_perishable=True
    )
    assert p.product_id == 1

def test_product_list_response():
    p = ProductResponse(
        product_id=1, product_name="A", category_id=2, 
        unit_cost=1.0, base_price=2.0, is_perishable=True
    )
    lr = ProductListResponse(
        total=1, page=1, page_size=20, total_pages=1, items=[p]
    )
    assert len(lr.items) == 1

def test_inventory_response():
    i = InventoryResponse(product_id=1, location_type="store", location_id=1, quantity=10, status="ok")
    assert i.quantity == 10

def test_inventory_alert():
    a = InventoryAlert(product_id=1, location_type="store", location_id=1, current_stock=5, reorder_point=10, severity="high")
    assert a.severity == "high"

def test_order_response():
    o = OrderResponse(order_id=1, store_id=1, product_id=1, quantity=10, status="pending")
    assert o.quantity == 10

def test_kpi_summary():
    k = KPISummary(total_revenue=100.0, total_profit=50.0, fill_rate=0.9, stockout_rate=0.1, on_time_delivery_rate=0.9, period_start="2020-01-01", period_end="2020-01-02")
    assert k.total_revenue == 100.0

def test_daily_kpi():
    d = DailyKPI(date="2020-01-01", revenue=100.0, profit=50.0, fill_rate=0.9)
    assert d.revenue == 100.0

def test_agent_status():
    a = AgentStatus(agent_name="agent1", status="active", tasks_today=10, success_rate=0.9, errors_today=1)
    assert a.success_rate == 0.9

def test_agent_decision_log():
    a = AgentDecisionLog(agent_name="agent1", action="order", details="Ordered 10", success=True)
    assert a.success is True

def test_config_update_request():
    c = ConfigUpdateRequest(values={"a": 1})
    assert c.section == "simulation"
    assert c.values["a"] == 1
