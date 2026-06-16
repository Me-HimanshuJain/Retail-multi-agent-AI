"""Real retail simulation environment using Multi-Agent optimization and Chaos Events.

Key fix in this version:
- _initialize_from_db() no longer crashes hard when the DB tables don't exist
  (e.g. in CI / test environments before migrations have run).
- Falls back to a small synthetic store/product/inventory set so the simulator
  can still be instantiated and run without a live database.
- All other logic (CoordinatorAgent, SmartInventoryAgent, spoilage, KPI math)
  is preserved exactly from the previous real version.
"""

from __future__ import annotations

import asyncio
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.simulation.demand_generator import DemandGenerator
from src.simulation.entities import SimulationDailyMetrics, SimulationRunMetrics
from src.simulation.external_factors import ExternalFactorsGenerator


# ---------------------------------------------------------------------------
# Fallback seed data — used when the DB is unavailable (CI, unit tests, etc.)
# ---------------------------------------------------------------------------
_FALLBACK_STORES = [
    {"id": 1, "name": "CA_1"},
    {"id": 2, "name": "CA_2"},
    {"id": 3, "name": "TX_1"},
]
_FALLBACK_PRODUCTS = [
    {"id": 1, "base_price": 3.99,  "unit_cost": 1.50, "shelf_life_days": 7},
    {"id": 2, "base_price": 12.49, "unit_cost": 5.00, "shelf_life_days": 30},
    {"id": 3, "base_price": 24.99, "unit_cost": 10.0, "shelf_life_days": 180},
]
_FALLBACK_STOCK = 80  # units per (store, product) pair at day 0


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

class CoordinatorAgent:
    """Network-level demand anomaly detector."""

    def __init__(self) -> None:
        self.network_demand_history: List[float] = []
        self.active_multiplier: float = 1.0

    def step(self, yesterday_total_demand: float) -> float:
        if yesterday_total_demand > 0:
            self.network_demand_history.append(yesterday_total_demand)

        if len(self.network_demand_history) < 4:
            return 1.0

        baseline = float(np.mean(self.network_demand_history[:-1][-7:]))
        if baseline <= 0:
            return 1.0

        if yesterday_total_demand > baseline * 2.0:
            self.active_multiplier = yesterday_total_demand / baseline
        else:
            self.active_multiplier = max(1.0, self.active_multiplier - 0.25)

        return self.active_multiplier


class SmartInventoryAgent:
    """AI-driven inventory optimisation for a single (store, product) pair."""

    def __init__(self, lead_time_days: int = 3) -> None:
        self.lead_time = lead_time_days
        self.pending_orders: List[Dict] = []
        self.total_orders_placed: int = 0
        self.total_units_ordered: int = 0

    def step(
        self,
        current_day: int,
        current_stock: int,
        generator: Optional[DemandGenerator],
        global_multiplier: float = 1.0,
    ) -> Tuple[int, int]:
        """Returns (units_arrived_today, units_ordered_today)."""
        arrived_today = sum(
            o["quantity"] for o in self.pending_orders if o["arrival_day"] <= current_day
        )
        self.pending_orders = [
            o for o in self.pending_orders if o["arrival_day"] > current_day
        ]

        if generator is None:
            return arrived_today, 0

        raw_forecast = generator.get_forecast_range(current_day, days=self.lead_time + 14)
        forecast = [max(0.0, d) * global_multiplier for d in raw_forecast]

        expected_demand_lt = sum(forecast[: self.lead_time])
        std_dev = float(np.std(forecast)) if forecast else 0.0
        safety_stock = int(1.28 * std_dev * np.sqrt(self.lead_time))

        reorder_point = int(expected_demand_lt) + safety_stock
        in_transit = sum(o["quantity"] for o in self.pending_orders)
        effective_inventory = current_stock + arrived_today + in_transit

        order_qty = 0
        if effective_inventory <= reorder_point:
            order_window = 3 if global_multiplier > 1.0 else 14
            expected_demand_window = sum(forecast[:order_window])
            order_up_to = int(expected_demand_window) + safety_stock
            order_qty = max(0, order_up_to - effective_inventory)
            if 0 < order_qty < 15:
                order_qty = 15
            if order_qty > 0:
                self.pending_orders.append(
                    {"arrival_day": current_day + self.lead_time, "quantity": order_qty}
                )
                self.total_orders_placed += 1
                self.total_units_ordered += order_qty

        return arrived_today, order_qty


# ---------------------------------------------------------------------------
# Main simulator
# ---------------------------------------------------------------------------

@dataclass
class RetailSimulator:
    seed: int = 42
    model_type: str = "xgb"
    start_date: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.start_date = self.start_date or datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.external_factors = ExternalFactorsGenerator(seed=self.seed)
        self.demand_generators: Dict[int, DemandGenerator] = {}
        self.inventory_agents: Dict[Tuple[int, int], SmartInventoryAgent] = {}
        self.coordinator = CoordinatorAgent()

        self.daily_metrics: List[SimulationDailyMetrics] = []
        self.db_inventory: Dict[Tuple[int, int], int] = {}
        self.product_prices: Dict[int, float] = {}
        self.product_costs: Dict[int, float] = {}
        self.product_shelf_life: Dict[int, int] = {}
        self.store_names: Dict[int, str] = {}

        self.active_demand_multiplier: float = 1.0
        self._db_available: bool = True

        # Track on-time delivery for KPI
        self._on_time_deliveries: int = 0
        self._total_deliveries: int = 0

        self._initialize_from_db()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialize_from_db(self) -> None:
        """Load stores/products/inventory from the database.

        If the DB is unavailable or tables don't exist yet (e.g. CI before
        migrations have run), falls back to a small synthetic dataset so the
        simulator can still be constructed and tested.
        """
        try:
            from sqlalchemy import text
            from src.core.database import SessionLocal

            db = SessionLocal()
            try:
                stores = db.execute(
                    text("SELECT id, name FROM stores")
                ).mappings().all()
                products = db.execute(
                    text("SELECT id, base_price, unit_cost, shelf_life_days FROM products")
                ).mappings().all()
                inventory = db.execute(
                    text(
                        "SELECT location_id, product_id, quantity "
                        "FROM inventory_snapshots WHERE location_type = 'store'"
                    )
                ).mappings().all()

                self._load_from_rows(stores, products, inventory)
            finally:
                db.close()

        except Exception as exc:
            warnings.warn(
                f"RetailSimulator: DB unavailable ({exc}). "
                "Using fallback synthetic store/product data."
            )
            self._db_available = False
            self._load_fallback()

    def _load_from_rows(self, stores, products, inventory) -> None:
        for p in products:
            self.product_prices[p["id"]] = float(p["base_price"])
            self.product_costs[p["id"]] = float(p.get("unit_cost", p["base_price"] * 0.5))
            self.product_shelf_life[p["id"]] = int(p.get("shelf_life_days", 30))
        for s in stores:
            self.store_names[s["id"]] = s["name"]
        for inv in inventory:
            sid, pid = inv["location_id"], inv["product_id"]
            self.db_inventory[(sid, pid)] = int(inv["quantity"])
            self.inventory_agents[(sid, pid)] = SmartInventoryAgent(lead_time_days=3)
        for s in stores:
            sid = s["id"]
            name = s["name"]
            try:
                self.demand_generators[sid] = DemandGenerator(
                    store_id=name,
                    model_type=self.model_type,
                    external_factors=self.external_factors,
                    start_date=self.start_date,
                    seed=self.seed,
                )
            except Exception as exc:
                warnings.warn(f"RetailSimulator: DemandGenerator for {name} failed: {exc}")

    def _load_fallback(self) -> None:
        """Populate simulator with minimal synthetic data for testing/CI."""
        for p in _FALLBACK_PRODUCTS:
            self.product_prices[p["id"]] = p["base_price"]
            self.product_costs[p["id"]] = p["unit_cost"]
            self.product_shelf_life[p["id"]] = p["shelf_life_days"]
        for s in _FALLBACK_STORES:
            sid = s["id"]
            self.store_names[sid] = s["name"]
            for p in _FALLBACK_PRODUCTS:
                pid = p["id"]
                self.db_inventory[(sid, pid)] = _FALLBACK_STOCK
                self.inventory_agents[(sid, pid)] = SmartInventoryAgent(lead_time_days=3)
            try:
                self.demand_generators[sid] = DemandGenerator(
                    store_id=s["name"],
                    model_type=self.model_type,
                    external_factors=self.external_factors,
                    start_date=self.start_date,
                    seed=self.seed,
                )
            except Exception as exc:
                warnings.warn(
                    f"RetailSimulator: DemandGenerator for {s['name']} failed: {exc}"
                )

    # ------------------------------------------------------------------
    # Disruption injection (called from API)
    # ------------------------------------------------------------------

    def inject_disruption(self, disruption_type: str, severity: str) -> None:
        if disruption_type == "viral_trend":
            self.active_demand_multiplier = 4.0 if severity == "high" else 2.5
        elif disruption_type == "supplier_delay":
            new_lead = 12 if severity == "high" else 7
            for agent in self.inventory_agents.values():
                agent.lead_time = new_lead
        elif disruption_type == "inventory_loss":
            loss_pct = 0.30 if severity == "high" else 0.15
            for key in self.db_inventory:
                self.db_inventory[key] = int(self.db_inventory[key] * (1 - loss_pct))

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------

    async def run(self, days: int = 30) -> Dict[str, float]:
        yesterday_total_demand = 0.0

        for day in range(days):
            daily_revenue = 0.0
            daily_demand = 0.0
            daily_sold = 0.0
            daily_lost = 0.0
            daily_stockouts = 0
            daily_holding_cost = 0.0
            daily_order_cost = 0.0
            daily_waste = 0.0
            daily_stockout_count = 0

            # Decay any active viral multiplier
            if self.active_demand_multiplier > 1.0:
                self.active_demand_multiplier = max(
                    1.0, self.active_demand_multiplier - 0.15
                )

            # 1. Coordinator reads yesterday's network demand
            network_multiplier = self.coordinator.step(yesterday_total_demand)

            sim_date = self.start_date + timedelta(days=day)  # type: ignore[operator]

            for (store_id, product_id), current_stock in list(self.db_inventory.items()):
                price = self.product_prices.get(product_id, 5.0)
                cost = self.product_costs.get(product_id, price * 0.5)
                shelf_life = self.product_shelf_life.get(product_id, 30)

                generator = self.demand_generators.get(store_id)
                agent = self.inventory_agents.get((store_id, product_id))

                # 2. Inventory agent places/receives orders
                if agent and generator:
                    arrived_stock, new_order = agent.step(
                        day, current_stock, generator,
                        global_multiplier=network_multiplier,
                    )
                    current_stock += arrived_stock

                    if new_order > 0:
                        daily_order_cost += 15.0
                        # Count on-time deliveries (simplified: all non-disrupted = on time)
                        self._total_deliveries += 1
                        if agent.lead_time <= 3:
                            self._on_time_deliveries += 1

                # 3. Compute demand from model / baseline, apply external factors
                factors = self.external_factors.generate(sim_date)
                ext_multiplier = factors.demand_multiplier

                if generator:
                    demand_raw = generator.get_demand(day)
                else:
                    demand_raw = 5.0

                demand = int(
                    max(0, demand_raw)
                    * self.active_demand_multiplier
                    * ext_multiplier
                )

                # 4. Sell
                sold = min(demand, current_stock)
                lost = demand - sold
                new_stock = current_stock - sold

                # 5. Spoilage — items that exceed shelf life on this day
                # Simple model: every unit in stock ages 1 day; anything
                # older than shelf_life_days is wasted.
                # We approximate spoilage as a fraction of ending stock
                # proportional to 1/shelf_life (daily turnover rate).
                spoilage_rate = 1.0 / max(shelf_life, 1)
                waste_today = int(new_stock * spoilage_rate)
                new_stock = max(0, new_stock - waste_today)
                daily_waste += waste_today

                # 6. Holding cost on remaining stock
                daily_holding_cost += new_stock * 0.10

                self.db_inventory[(store_id, product_id)] = new_stock

                daily_demand += demand
                daily_sold += sold
                daily_lost += lost
                daily_revenue += sold * price

                if demand > current_stock:
                    daily_stockouts += 1
                    daily_stockout_count += 1

            yesterday_total_demand = daily_demand

            fill_rate = (daily_sold / daily_demand) if daily_demand > 0 else 1.0
            # Profit = gross margin - holding costs - order costs - waste write-off
            avg_cost = (
                sum(self.product_costs.values()) / len(self.product_costs)
                if self.product_costs else 2.50
            )
            daily_profit = (
                daily_revenue * 0.40
                - daily_holding_cost
                - daily_order_cost
                - (daily_waste * avg_cost)
            )

            self.daily_metrics.append(
                SimulationDailyMetrics(
                    day=day,
                    total_revenue=daily_revenue,
                    total_demand=daily_demand,
                    total_sold=daily_sold,
                    total_lost_sales=daily_lost,
                    fill_rate=fill_rate,
                    stockout_occurred=daily_stockouts > 0,
                    waste_units=daily_waste,
                    daily_profit=daily_profit,
                    stockout_count=daily_stockout_count,
                )
            )

            await asyncio.sleep(0)  # yield to event loop

        if self._db_available:
            self._flush_inventory_to_db()

        return self.get_metrics()

    # ------------------------------------------------------------------
    # DB write-back
    # ------------------------------------------------------------------

    def _flush_inventory_to_db(self) -> None:
        try:
            from sqlalchemy import text
            from src.core.database import SessionLocal

            db = SessionLocal()
            try:
                for (store_id, product_id), stock in self.db_inventory.items():
                    db.execute(
                        text(
                            """
                            UPDATE inventory_snapshots
                            SET quantity = :qty, updated_at = CURRENT_TIMESTAMP
                            WHERE location_id = :sid
                              AND product_id = :pid
                              AND location_type = 'store'
                            """
                        ),
                        {"qty": stock, "sid": store_id, "pid": product_id},
                    )
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception as exc:
            warnings.warn(f"RetailSimulator: DB flush failed: {exc}")

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, float]:
        on_time = (
            self._on_time_deliveries / self._total_deliveries
            if self._total_deliveries > 0
            else 1.0
        )
        run = SimulationRunMetrics.from_daily(self.daily_metrics, on_time_rate=on_time)
        return {
            "total_revenue":        run.total_revenue,
            "total_profit":         run.total_profit,
            "fill_rate":            run.avg_fill_rate,
            "stockout_rate":        run.stockout_rate,
            "service_level":        run.service_level,
            "waste_rate":           run.waste_rate,
            "total_waste_units":    run.total_waste_units,
            "total_lost_sales":     run.total_lost_sales,
            "on_time_delivery_rate": run.on_time_delivery_rate,
            "days_simulated":       float(run.days_simulated),
        }

    def get_daily_metrics(self) -> List[SimulationDailyMetrics]:
        return list(self.daily_metrics)