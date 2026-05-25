"""Simulation entity dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Product:
    product_id: int
    name: str
    unit_cost: float
    base_price: float
    shelf_life_days: int

    @property
    def margin(self) -> float:
        if self.base_price == 0:
            return 0.0
        return (self.base_price - self.unit_cost) / self.base_price


@dataclass
class Store:
    store_id: int
    name: str
    region: str
    size_sqft: int
    lat: float
    lon: float
    inventory: Dict[int, int] = field(default_factory=dict)

    def update_stock(self, product_id: int, delta: int) -> None:
        self.inventory[product_id] = max(0, self.inventory.get(product_id, 0) + delta)

    def get_stock(self, product_id: int) -> int:
        return self.inventory.get(product_id, 0)


@dataclass
class Warehouse:
    warehouse_id: int
    name: str
    warehouse_type: str
    capacity: int
    lat: float
    lon: float
    inventory: Dict[int, int] = field(default_factory=dict)

    def update_stock(self, product_id: int, delta: int) -> None:
        self.inventory[product_id] = max(0, self.inventory.get(product_id, 0) + delta)

    @property
    def current_utilization(self) -> float:
        if self.capacity == 0:
            return 0.0
        return sum(self.inventory.values()) / self.capacity

    def can_accept(self, quantity: int) -> bool:
        return sum(self.inventory.values()) + quantity <= self.capacity


@dataclass
class Supplier:
    supplier_id: int
    name: str
    reliability_score: float
    avg_lead_time_days: int
    total_orders: int = 0
    successful_orders: int = 0

    def record_order_result(self, success: bool) -> None:
        self.total_orders += 1
        if success:
            self.successful_orders += 1


@dataclass
class Shipment:
    shipment_id: str
    product_id: int
    quantity: int
    origin: str
    destination: str


@dataclass
class SimulationState:
    day: int = 0
    revenue: float = 0.0
    profit: float = 0.0
    fill_rate: float = 0.0
