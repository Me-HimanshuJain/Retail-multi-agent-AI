"""Shared API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class APIError(BaseModel):
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProductResponse(BaseModel):
    product_id: int
    product_name: str
    category_id: int
    unit_cost: float
    base_price: float
    is_perishable: bool


class ProductListResponse(PaginatedResponse):
    items: List[ProductResponse]


class InventoryResponse(BaseModel):
    product_id: int
    location_type: str
    location_id: int
    quantity: int
    status: str


class InventoryAlert(BaseModel):
    product_id: int
    location_type: str
    location_id: int
    current_stock: int
    reorder_point: int
    severity: str


class OrderResponse(BaseModel):
    order_id: int
    store_id: int
    product_id: int
    quantity: int
    status: str


class KPISummary(BaseModel):
    total_revenue: float
    total_profit: float
    fill_rate: float
    stockout_rate: float
    on_time_delivery_rate: float
    period_start: str
    period_end: str


class DailyKPI(BaseModel):
    date: str
    revenue: float
    profit: float
    fill_rate: float


class AgentStatus(BaseModel):
    agent_name: str
    status: str
    tasks_today: int
    success_rate: float
    errors_today: int


class AgentDecisionLog(BaseModel):
    agent_name: str
    action: str
    details: str
    success: bool
    execution_time_ms: Optional[int] = None


class ConfigUpdateRequest(BaseModel):
    section: str = "simulation"
    values: dict
