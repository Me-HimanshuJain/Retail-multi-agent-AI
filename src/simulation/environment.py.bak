"""Retail simulation environment."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List

from src.core.events import DemandForecastUpdated, RestockRequest
from src.simulation.entities import Product, Store, Supplier, Warehouse
from src.simulation.external_factors import ExternalFactorsGenerator


@dataclass
class RetailSimulator:
    seed: int = 42
    products: List[Product] = field(default_factory=list)
    stores: List[Store] = field(default_factory=list)
    warehouses: List[Warehouse] = field(default_factory=list)
    suppliers: List[Supplier] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=lambda: {"revenue": 0.0, "profit": 0.0, "fill_rate": 0.0, "stockout_rate": 0.0, "on_time_delivery_rate": 0.0})

    def __post_init__(self) -> None:
        if not self.products:
            self.products = [Product(1, "Milk", 2.0, 4.0, 14)]
        if not self.stores:
            self.stores = [Store(1, "Demo Store", "East", 1000, 40.0, -74.0)]
        if not self.warehouses:
            self.warehouses = [Warehouse(1, "Demo DC", "DC", 10000, 40.0, -74.0)]
        if not self.suppliers:
            self.suppliers = [Supplier(1, "Demo Supplier", 0.95, 3)]
        self.external_factors = ExternalFactorsGenerator(seed=self.seed)

    async def run(self, days: int = 30) -> Dict[str, float]:
        for day in range(days):
            self.metrics["revenue"] += 1000 + day * 10
            self.metrics["profit"] += 150 + day * 2
            self.metrics["fill_rate"] = 0.95
            await asyncio.sleep(0)
        return self.metrics

    def get_metrics(self) -> Dict[str, float]:
        return self.metrics
