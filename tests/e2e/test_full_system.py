from __future__ import annotations

import asyncio

from src.simulation.environment import RetailSimulator


def test_simulator_runs():
    sim = RetailSimulator()
    metrics = asyncio.run(sim.run(1))
    assert "revenue" in metrics
