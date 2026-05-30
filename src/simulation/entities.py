"""Simulation entity dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Product:
    product_id: int
    name: str
    unit_cost: float
    base_price: float
    shelf_life_days: int
    category: str = "general"

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
    reliability_score: float          # 0.0–1.0; probability a shipment arrives on time
    avg_lead_time_days: int
    total_orders: int = 0
    successful_orders: int = 0

    def record_order_result(self, success: bool) -> None:
        self.total_orders += 1
        if success:
            self.successful_orders += 1

    @property
    def observed_reliability(self) -> float:
        """Empirical reliability based on recorded order history."""
        if self.total_orders == 0:
            return self.reliability_score
        return self.successful_orders / self.total_orders


@dataclass
class Shipment:
    shipment_id: str
    product_id: int
    quantity: int
    origin: str
    destination: str
    # Arrival tracking — previously missing, caused supplier logic to be unused
    scheduled_arrival_day: int = 0    # day number the shipment was supposed to arrive
    actual_arrival_day: Optional[int] = None   # set when it actually arrives (may differ if delayed)
    delivered: bool = False
    delayed: bool = False
    delay_days: int = 0

    def mark_delivered(self, actual_day: int) -> None:
        self.actual_arrival_day = actual_day
        self.delivered = True
        if actual_day > self.scheduled_arrival_day:
            self.delayed = True
            self.delay_days = actual_day - self.scheduled_arrival_day

    @property
    def on_time(self) -> bool:
        return self.delivered and not self.delayed


@dataclass
class InventoryBatch:
    """
    Tracks a single batch of received stock for aging / spoilage purposes.
    Previously the simulation had no concept of when stock arrived, so
    waste_units was always 0.0. Now each replenishment creates a batch
    with a receive_day, and the simulation can expire old batches.
    """
    product_id: int
    quantity: int
    receive_day: int
    shelf_life_days: int

    @property
    def expiry_day(self) -> int:
        return self.receive_day + self.shelf_life_days

    def units_expired_on_day(self, current_day: int) -> int:
        """Return units that expire exactly on current_day (for waste accounting)."""
        if current_day == self.expiry_day and not self._expired:
            self._expired = True
            return self.quantity
        return 0

    def __post_init__(self) -> None:
        self._expired = False


@dataclass
class SimulationDailyMetrics:
    """Per-day metrics snapshot — one instance per simulation day."""
    day: int
    total_revenue: float
    total_demand: float
    total_sold: float
    total_lost_sales: float
    fill_rate: float
    stockout_occurred: bool
    waste_units: float
    daily_profit: float = 0.0
    holding_cost: float = 0.0
    order_cost: float = 0.0
    stockout_count: int = 0         # number of (store, product) pairs that hit zero stock
    on_time_deliveries: int = 0     # shipments that arrived on schedule today
    late_deliveries: int = 0        # shipments that arrived late today


@dataclass
class SimulationRunMetrics:
    """
    Aggregated metrics over a full simulation run.
    Previously metrics were computed inline in get_metrics(); having a
    dedicated dataclass makes it easy to serialise, compare scenarios,
    and return from the API without further processing.
    """
    total_revenue: float = 0.0
    total_profit: float = 0.0
    avg_fill_rate: float = 0.0
    stockout_rate: float = 0.0          # fraction of days where any stockout occurred
    service_level: float = 0.0          # fraction of total demand that was met
    avg_waste_units: float = 0.0
    total_waste_units: float = 0.0
    on_time_delivery_rate: float = 0.0  # computed from actual shipment records, not hardcoded
    inventory_turnover: float = 0.0     # total_sold / avg_inventory_level (if tracked)
    days_simulated: int = 0


@dataclass
class SimulationState:
    """
    Running totals updated each day by RetailSimulator.run().
    Previously only held day/revenue/profit/fill_rate with no deeper state.
    """
    day: int = 0
    revenue: float = 0.0
    profit: float = 0.0
    fill_rate: float = 0.0
    # Shipment ledger — populated by SmartInventoryAgent orders
    pending_shipments: List[Shipment] = field(default_factory=list)
    delivered_shipments: List[Shipment] = field(default_factory=list)

    def record_shipment(self, shipment: Shipment) -> None:
        self.pending_shipments.append(shipment)

    def process_arrivals(self, current_day: int) -> List[Shipment]:
        """
        Move any shipments whose actual_arrival_day == current_day
        from pending to delivered and return them so the caller can
        add the quantity to inventory.
        """
        arrived = [s for s in self.pending_shipments if s.scheduled_arrival_day <= current_day]
        for s in arrived:
            s.mark_delivered(current_day)
            self.delivered_shipments.append(s)
        self.pending_shipments = [s for s in self.pending_shipments if s.scheduled_arrival_day > current_day]
        return arrived

    @property
    def on_time_delivery_rate(self) -> float:
        """
        Computed from actual shipment records — replaces the hardcoded 0.98.
        Returns 1.0 (perfect) when no shipments have been delivered yet
        to avoid a misleading 0.0 at startup.
        """
        if not self.delivered_shipments:
            return 1.0
        on_time = sum(1 for s in self.delivered_shipments if s.on_time)
        return on_time / len(self.delivered_shipments)