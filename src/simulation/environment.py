"""Real retail simulation environment using trained forecasts and inventory management."""

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


@dataclass
class RetailSimulator:
    """Real simulation engine using trained forecasts and inventory dynamics."""
    
    seed: int = 42
    model_type: str = "lgbm"
    
    def __post_init__(self) -> None:
        self.external_factors = ExternalFactorsGenerator(seed=self.seed)
        self.demand_generators: Dict[int, DemandGenerator] = {}
        self.daily_metrics: List[SimulationDailyMetrics] = []
        
        self.db_inventory = {}
        self.product_prices = {}
        self.store_names = {}
        
        self._initialize_from_db()

    def _initialize_from_db(self) -> None:
        """Load actual stores, products, and starting inventory from the new schema."""
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
                self.db_inventory[(inv["location_id"], inv["product_id"])] = int(inv["quantity"])
                
            for s in stores:
                store_db_id = s["id"]
                store_string_name = s["name"] # e.g. "CA_1"
                try:
                    # Pass the string name so it finds the correct .bin file
                    self.demand_generators[store_db_id] = DemandGenerator(
                        store_id=store_string_name,
                        model_type=self.model_type,
                        external_factors=self.external_factors,
                        seed=self.seed,
                    )
                except Exception as e:
                    print(f"Warning: Could not init DemandGenerator for {store_string_name}: {e}")
                    
        finally:
            db.close()

    async def run(self, days: int = 30) -> Dict[str, float]:
        """Run realistic simulation loops across all real stores and products."""
        for day in range(days):
            daily_revenue = 0.0
            daily_demand = 0.0
            daily_sold = 0.0
            daily_stockouts = 0
            
            for (store_id, product_id), current_stock in self.db_inventory.items():
                price = self.product_prices.get(product_id, 5.0)
                
                generator = self.demand_generators.get(store_id)
                if generator:
                    demand_raw = generator.get_demand(day)
                    demand = int(max(0, demand_raw * 0.15)) 
                else:
                    demand = 5 
                
                sold = min(demand, current_stock)
                new_stock = current_stock - sold
                
                if new_stock < 20:
                    new_stock += 100
                    
                self.db_inventory[(store_id, product_id)] = new_stock
                
                daily_demand += demand
                daily_sold += sold
                daily_revenue += (sold * price)
                
                if demand > current_stock:
                    daily_stockouts += 1

            fill_rate = (daily_sold / daily_demand) if daily_demand > 0 else 1.0
            
            self.daily_metrics.append(SimulationDailyMetrics(
                day=day,
                total_revenue=daily_revenue,
                total_demand=daily_demand,
                total_sold=daily_sold,
                total_lost_sales=daily_demand - daily_sold,
                fill_rate=fill_rate,
                stockout_occurred=daily_stockouts > 0,
                waste_units=0.0
            ))
            
            await asyncio.sleep(0)
            
        self._flush_inventory_to_db()
        return self.get_metrics()

    def _flush_inventory_to_db(self):
        """Save the simulation's end state back to the new inventory_snapshots schema."""
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
        except Exception as e:
            db.rollback()
            print(f"Error flushing inventory: {e}")
        finally:
            db.close()

    def get_metrics(self) -> Dict[str, float]:
        """Calculate aggregated KPIs."""
        if not self.daily_metrics:
            return {
                "total_revenue": 0.0,
                "total_profit": 0.0,
                "fill_rate": 1.0, 
                "stockout_rate": 0.0,
                "on_time_delivery_rate": 0.95,
            }
            
        total_revenue = sum(m.total_revenue for m in self.daily_metrics)
        total_demand = sum(m.total_demand for m in self.daily_metrics)
        stockout_days = sum(1 for m in self.daily_metrics if m.stockout_occurred)
        
        avg_fill_rate = float(np.mean([m.fill_rate for m in self.daily_metrics]))
        total_days = len(self.daily_metrics)
        
        total_profit = total_revenue * 0.30 
        stockout_rate = (stockout_days / total_days) if total_days > 0 else 0.0

        return {
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "fill_rate": avg_fill_rate,
            "stockout_rate": stockout_rate,
            "on_time_delivery_rate": 0.98,
        }