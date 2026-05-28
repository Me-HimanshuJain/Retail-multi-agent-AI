"""Real inventory simulation with depletion, restocking, and aging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np


@dataclass
class InventoryBatch:
    """Track inventory by received date for aging/spoilage."""

    batch_id: str
    received_date: datetime
    shelf_life_days: int
    unit_cost: float
    quantity: int

    @property
    def age_days(self) -> int:
        """Days since received (from a fixed reference point for simulation)."""
        return (datetime(2020, 1, 1) - self.received_date).days

    @property
    def is_expired(self) -> bool:
        """Whether batch has expired."""
        return self.age_days >= self.shelf_life_days

    @property
    def days_until_expiry(self) -> int:
        """Days until expiration."""
        return max(0, self.shelf_life_days - self.age_days)


@dataclass
class InventorySnapshot:
    """Daily inventory snapshot for KPI tracking."""

    day: int
    on_hand: float
    on_order: float
    total_received: float
    total_sold: float
    total_lost_sales: float
    total_waste: float
    fill_rate: float
    stockout_occurred: bool


class InventorySimulator:
    """Simulate store inventory with realistic depletion, restocking, and aging."""

    def __init__(
        self,
        product_id: int,
        store_id: str,
        unit_cost: float,
        base_price: float,
        shelf_life_days: int,
        initial_inventory: float = 100.0,
        reorder_point: float = 20.0,
        reorder_quantity: float = 50.0,
        lead_time_days: int = 3,
        lead_time_std_days: float = 1.0,
    ):
        """
        Initialize inventory simulator.

        Args:
            product_id: Product identifier
            store_id: Store identifier
            unit_cost: Cost per unit
            base_price: Selling price per unit
            shelf_life_days: Days until expiration
            initial_inventory: Starting quantity
            reorder_point: Reorder when below this level
            reorder_quantity: Order this many units when reordering
            lead_time_days: Expected days to receive order
            lead_time_std_days: Standard deviation of lead time
        """
        self.product_id = product_id
        self.store_id = store_id
        self.unit_cost = unit_cost
        self.base_price = base_price
        self.shelf_life_days = shelf_life_days
        self.reorder_point = reorder_point
        self.reorder_quantity = reorder_quantity
        self.lead_time_days = lead_time_days
        self.lead_time_std_days = lead_time_std_days

        # Inventory state
        self.on_hand: Dict[int, float] = {0: initial_inventory}
        self.batches: List[InventoryBatch] = []
        self.on_order: Dict[int, float] = {}  # day -> quantity on order
        self.pending_shipments: List[tuple[int, float]] = []  # (arrival_day, qty)

        # Metrics
        self.daily_snapshots: List[InventorySnapshot] = []
        self.total_cost_cogs = 0.0
        self.total_revenue = 0.0
        self.total_stockout_cost = 0.0
        self.total_waste_cost = 0.0
        self.total_transport_cost = 0.0

        self.rng = np.random.RandomState(42)

    def process_incoming_shipments(self, day: int) -> float:
        """Process any shipments arriving today. Returns quantity received."""
        received = 0.0
        remaining_shipments = []

        for arrival_day, qty in self.pending_shipments:
            if arrival_day <= day:
                received += qty
                self._add_inventory_batch(day, qty)
            else:
                remaining_shipments.append((arrival_day, qty))

        self.pending_shipments = remaining_shipments
        return received

    def _add_inventory_batch(self, received_day: int, quantity: float) -> None:
        """Add inventory batch with tracking info."""
        batch_id = f"{self.store_id}_{self.product_id}_{received_day}"
        batch = InventoryBatch(
            batch_id=batch_id,
            received_date=datetime(2020, 1, 1) + timedelta(days=received_day),
            shelf_life_days=self.shelf_life_days,
            unit_cost=self.unit_cost,
            quantity=int(quantity),
        )
        self.batches.append(batch)

    def remove_expired_inventory(self, day: int) -> float:
        """Remove expired inventory and return waste units. Update waste cost."""
        expired_quantity = 0.0
        remaining_batches = []

        for batch in self.batches:
            if batch.is_expired:
                expired_quantity += batch.quantity
                self.total_waste_cost += batch.quantity * batch.unit_cost
            else:
                remaining_batches.append(batch)

        self.batches = remaining_batches
        return expired_quantity

    def process_demand(self, day: int, demand: float, price_delta_pct: float = 0.0) -> tuple[float, float, float]:
        """
        Process customer demand.

        Args:
            day: Day number
            demand: Demand quantity
            price_delta_pct: Price change percentage

        Returns:
            (units_sold, lost_sales, revenue)
        """
        # Calculate available inventory
        available = sum(batch.quantity for batch in self.batches)

        # Fulfill demand up to available supply
        units_sold = min(demand, available)
        lost_sales = max(0.0, demand - available)

        # Update batches (FIFO - sell oldest first to reduce waste)
        remaining_demand = units_sold
        for batch in self.batches:
            if remaining_demand <= 0:
                break
            sold_from_batch = min(remaining_demand, batch.quantity)
            batch.quantity -= int(sold_from_batch)
            remaining_demand -= sold_from_batch

        # Remove empty batches
        self.batches = [b for b in self.batches if b.quantity > 0]

        # Calculate revenue
        effective_price = self.base_price * (1.0 + price_delta_pct / 100.0)
        revenue = units_sold * effective_price

        # Update costs
        self.total_cost_cogs += units_sold * self.unit_cost
        self.total_revenue += revenue

        # Stockout penalty
        if lost_sales > 0:
            stockout_penalty_rate = 0.5  # 50% of margin lost per lost sale
            self.total_stockout_cost += lost_sales * effective_price * stockout_penalty_rate

        return units_sold, lost_sales, revenue

    def check_and_place_reorder(self, day: int) -> Optional[float]:
        """
        Check if reorder is needed and schedule shipment.

        Args:
            day: Current day

        Returns:
            Order quantity if placed, None otherwise
        """
        available = sum(batch.quantity for batch in self.batches)

        if available < self.reorder_point:
            # Calculate lead time with variance
            lead_time = int(max(1, np.random.normal(self.lead_time_days, self.lead_time_std_days)))
            arrival_day = day + lead_time

            # Add to pending shipments
            self.pending_shipments.append((arrival_day, self.reorder_quantity))

            # Add transport cost (simplified: cost per unit * distance factor)
            transport_cost = self.reorder_quantity * self.unit_cost * 0.05  # 5% of COGS
            self.total_transport_cost += transport_cost

            return self.reorder_quantity
        return None

    def step(
        self,
        day: int,
        demand: float,
        price_delta_pct: float = 0.0,
        check_reorder: bool = True,
    ) -> InventorySnapshot:
        """
        Process one day of inventory simulation.

        Args:
            day: Day number
            demand: Customer demand
            price_delta_pct: Price change percentage
            check_reorder: Whether to check and place reorders

        Returns:
            Daily snapshot
        """
        # Process incoming shipments
        received = self.process_incoming_shipments(day)

        # Remove expired inventory
        waste = self.remove_expired_inventory(day)

        # Process customer demand
        units_sold, lost_sales, revenue = self.process_demand(day, demand, price_delta_pct)

        # Check inventory level and reorder if needed
        on_order = sum(qty for _, qty in self.pending_shipments)
        if check_reorder:
            self.check_and_place_reorder(day)

        # Calculate current inventory
        on_hand = sum(batch.quantity for batch in self.batches)

        # Calculate fill rate
        total_demand = units_sold + lost_sales
        fill_rate = (units_sold / total_demand) if total_demand > 0 else 1.0

        # Create snapshot
        snapshot = InventorySnapshot(
            day=day,
            on_hand=float(on_hand),
            on_order=float(on_order),
            total_received=received,
            total_sold=units_sold,
            total_lost_sales=lost_sales,
            total_waste=waste,
            fill_rate=float(fill_rate),
            stockout_occurred=lost_sales > 0,
        )

        self.daily_snapshots.append(snapshot)
        self.on_hand[day] = on_hand

        return snapshot

    def get_kpis(self) -> Dict[str, float]:
        """Calculate aggregated KPIs across all days."""
        if not self.daily_snapshots:
            return {
                "revenue": 0.0,
                "profit": 0.0,
                "avg_inventory": 0.0,
                "fill_rate": 1.0,
                "stockout_rate": 0.0,
                "waste_rate": 0.0,
                "inventory_turnover": 0.0,
                "service_level": 1.0,
            }

        total_days = len(self.daily_snapshots)
        total_demand = sum(s.total_sold + s.total_lost_sales for s in self.daily_snapshots)
        total_sold = sum(s.total_sold for s in self.daily_snapshots)
        total_lost = sum(s.total_lost_sales for s in self.daily_snapshots)
        total_waste = sum(s.total_waste for s in self.daily_snapshots)
        avg_inventory = np.mean([s.on_hand for s in self.daily_snapshots]) if self.daily_snapshots else 0.0
        stockout_days = sum(1 for s in self.daily_snapshots if s.stockout_occurred)

        profit = self.total_revenue - self.total_cost_cogs - self.total_stockout_cost - self.total_waste_cost - self.total_transport_cost
        inventory_turnover = self.total_cost_cogs / avg_inventory if avg_inventory > 0 else 0.0
        service_level = 1.0 - (total_lost / total_demand) if total_demand > 0 else 1.0
        waste_rate = (total_waste / total_demand * 100.0) if total_demand > 0 else 0.0

        return {
            "revenue": self.total_revenue,
            "profit": profit,
            "avg_inventory": avg_inventory,
            "fill_rate": total_sold / total_demand if total_demand > 0 else 1.0,
            "stockout_rate": stockout_days / total_days * 100.0,
            "waste_rate": waste_rate,
            "inventory_turnover": inventory_turnover,
            "service_level": service_level * 100.0,
        }
