from __future__ import annotations

import asyncio

from src.simulation.environment import RetailSimulator


def test_simulator_runs():
    sim = RetailSimulator()
    metrics = asyncio.run(sim.run(1))
    assert "total_revenue" in metrics
    assert "total_profit" in metrics
    assert "fill_rate" in metrics
    assert metrics["fill_rate"] >= 0.0
    assert metrics["fill_rate"] <= 1.0