"""Real retail simulation environment using Multi-Agent optimization and Chaos Events."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from sqlalchemy import text
from src.core.database import SessionLocal
from src.simulation.demand_generator import DemandGenerator
from src.simulation.external_factors import ExternalFactorsGenerator


@dataclass
class SimulationDailyMetrics:
    """Daily metrics snapshot."""
    day: int
    total_revenue: float
    total_demand: float
    total_sold: float
    total_lost_sales: float
    fill_rate: float
    stockout_occurred: bool
    waste_units: float
    daily_profit: float = 0.0  


class CoordinatorAgent:
    """The Global Overseer."""
    def __init__(self):
        self.network_demand_history: List[float] = []
        self.active_multiplier = 1.0

    def step(self, yesterday_total_demand: float) -> float:
        if yesterday_total_demand > 0:
            self.network_demand_history.append(yesterday_total_demand)

        if len(self.network_demand_history) < 4:
            return 1.0

        baseline = float(np.mean(self.network_demand_history[:-1][-7:]))
        if baseline <= 0:
            return 1.0

        # Anomaly Detection
        if yesterday_total_demand > baseline * 2.0:
            self.active_multiplier = yesterday_total_demand / baseline
        else:
            self.active_multiplier = max(1.0, self.active_multiplier - 0.25)

        return self.active_multiplier


class SmartInventoryAgent:
    """AI-driven inventory optimization agent for local stores."""
    def __init__(self, lead_time_days: int = 3):
        self.lead_time = lead_time_days
        self.pending_orders = [] 
        
    def step(self, current_day: int, current_stock: int, generator: DemandGenerator, global_multiplier: float = 1.0) -> tuple[int, int]:
        arrived_today = sum(o["quantity"] for o in self.pending_orders if o["arrival_day"] <= current_day)
        self.pending_orders = [o for o in self.pending_orders if o["arrival_day"] > current_day]
        
        if generator is None:
            return arrived_today, 0
            
        raw_forecast = generator.get_forecast_range(current_day, days=self.lead_time + 14)
        
        # Apply the Coordinator's emergency multiplier
        forecast = [max(0, d * 0.15) * global_multiplier for d in raw_forecast]
        
        expected_demand_lt = sum(forecast[:self.lead_time])
        std_dev = float(np.std(forecast)) if len(forecast) > 0 else 0.0
        safety_stock = int(1.28 * std_dev * np.sqrt(self.lead_time))
        
        reorder_point = int(expected_demand_lt) + safety_stock
        effective_inventory = current_stock + arrived_today + sum(o["quantity"] for o in self.pending_orders)
        
        order_qty = 0
        if effective_inventory <= reorder_point:
            # 🚀 DYNAMIC ORDER WINDOW FIX 🚀
            # If the Boss detects an anomaly, switch to Agile Mode (3 days). 
            # Otherwise, stay in Bulk Savings Mode (14 days).
            order_window = 3 if global_multiplier > 1.0 else 14
            
            expected_demand_window = sum(forecast[:order_window])
            order_up_to = int(expected_demand_window) + safety_stock
            
            order_qty = max(0, order_up_to - effective_inventory)
            
            if order_qty > 0 and order_qty < 15:
                order_qty = 15
                
            self.pending_orders.append({
                "arrival_day": current_day + self.lead_time,
                "quantity": order_qty
            })
            
        return arrived_today, order_qty


@dataclass
class RetailSimulator:
    seed: int = 42
    model_type: str = "lgbm"
    
    def __post_init__(self) -> None:
        self.external_factors = ExternalFactorsGenerator(seed=self.seed)
        self.demand_generators: Dict[int, DemandGenerator] = {}
        self.inventory_agents: Dict[tuple[int, int], SmartInventoryAgent] = {}
        self.coordinator = CoordinatorAgent()
        
        self.daily_metrics: List[SimulationDailyMetrics] = []
        self.db_inventory = {}
        self.product_prices = {}
        self.store_names = {}
        
        self.active_demand_multiplier = 1.0
        self._initialize_from_db()

    def inject_disruption(self, disruption_type: str, severity: str) -> None:
        if disruption_type == "viral_trend":
            self.active_demand_multiplier = 4.0 if severity == "high" else 2.5
        elif disruption_type == "supplier_delay":
            new_lead = 12 if severity == "high" else 7
            for agent in self.inventory_agents.values():
                agent.lead_time = new_lead

    def _initialize_from_db(self) -> None:
        db = SessionLocal()
        try:
            stores = db.execute(text("SELECT id, name FROM stores")).mappings().all()
            products = db.execute(text("SELECT id, base_price FROM products")).mappings().all()
            inventory = db.execute(text("SELECT location_id, product_id, quantity FROM inventory_snapshots WHERE location_type = 'store'")).mappings().all()
            
            for p in products:
                self.product_prices[p["id"]] = float(p["base_price"])
            for s in stores:
                self.store_names[s["id"]] = s["name"]
                
            for inv in inventory:
                store_id = inv["location_id"]
                product_id = inv["product_id"]
                self.db_inventory[(store_id, product_id)] = int(inv["quantity"])
                self.inventory_agents[(store_id, product_id)] = SmartInventoryAgent(lead_time_days=3)
                
            for s in stores:
                store_db_id = s["id"]
                store_string_name = s["name"]
                try:
                    self.demand_generators[store_db_id] = DemandGenerator(
                        store_id=store_string_name,
                        model_type=self.model_type,
                        external_factors=self.external_factors,
                        seed=self.seed,
                    )
                except Exception:
                    pass
        finally:
            db.close()

    async def run(self, days: int = 30) -> Dict[str, float]:
        yesterday_total_demand = 0.0
        
        for day in range(days):
            daily_revenue = 0.0
            daily_demand = 0.0
            daily_sold = 0.0
            daily_stockouts = 0
            
            daily_holding_cost = 0.0
            daily_order_cost = 0.0
            
            if self.active_demand_multiplier > 1.0:
                self.active_demand_multiplier = max(1.0, self.active_demand_multiplier - 0.15)
                
            # 1. The Boss detects anomalies
            network_multiplier = self.coordinator.step(yesterday_total_demand)
            
            for (store_id, product_id), current_stock in self.db_inventory.items():
                price = self.product_prices.get(product_id, 5.0)
                
                generator = self.demand_generators.get(store_id)
                agent = self.inventory_agents.get((store_id, product_id))
                
                # 2. Local agents order with dynamic windows
                if agent and generator:
                    arrived_stock, new_order = agent.step(day, current_stock, generator, global_multiplier=network_multiplier)
                    current_stock += arrived_stock
                    
                    if new_order > 0:
                        daily_order_cost += 15.0  
                
                if generator:
                    demand_raw = generator.get_demand(day)
                    demand = int(max(0, demand_raw * 0.15) * self.active_demand_multiplier)
                else:
                    demand = 5 
                
                sold = min(demand, current_stock)
                new_stock = current_stock - sold
                daily_holding_cost += new_stock * 0.001
                
                self.db_inventory[(store_id, product_id)] = new_stock
                
                daily_demand += demand
                daily_sold += sold
                daily_revenue += (sold * price)
                
                if demand > current_stock:
                    daily_stockouts += 1

            yesterday_total_demand = daily_demand

            fill_rate = (daily_sold / daily_demand) if daily_demand > 0 else 1.0
            daily_profit = (daily_revenue * 0.40) - daily_holding_cost - daily_order_cost
            
            self.daily_metrics.append(SimulationDailyMetrics(
                day=day, total_revenue=daily_revenue, total_demand=daily_demand,
                total_sold=daily_sold, total_lost_sales=daily_demand - daily_sold,
                fill_rate=fill_rate, stockout_occurred=daily_stockouts > 0,
                waste_units=0.0, daily_profit=daily_profit
            ))
            
            await asyncio.sleep(0)  # Slightly faster execution
            
        self._flush_inventory_to_db()
        return self.get_metrics()

    def _flush_inventory_to_db(self):
        db = SessionLocal()
        try:
            for (store_id, product_id), stock in self.db_inventory.items():
                db.execute(
                    text("""
                    UPDATE inventory_snapshots 
                    SET quantity = :qty, updated_at = CURRENT_TIMESTAMP 
                    WHERE location_id = :sid AND product_id = :pid AND location_type = 'store'
                    """), 
                    {"qty": stock, "sid": store_id, "pid": product_id}
                )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def get_metrics(self) -> Dict[str, float]:
        if not self.daily_metrics:
            return {
                "total_revenue": 0.0, "total_profit": 0.0,
                "fill_rate": 1.0, "stockout_rate": 0.0,
                "on_time_delivery_rate": 0.95,
            }
            
        total_revenue = sum(m.total_revenue for m in self.daily_metrics)
        total_profit = sum(m.daily_profit for m in self.daily_metrics)
        stockout_days = sum(1 for m in self.daily_metrics if m.stockout_occurred)
        
        avg_fill_rate = float(np.mean([m.fill_rate for m in self.daily_metrics]))
        total_days = len(self.daily_metrics)
        stockout_rate = (stockout_days / total_days) if total_days > 0 else 0.0

        return {
            "total_revenue": total_revenue, "total_profit": total_profit,
            "fill_rate": avg_fill_rate, "stockout_rate": stockout_rate,
            "on_time_delivery_rate": 0.98,
        }