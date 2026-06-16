import pytest
from src.simulation.environment import RetailSimulator

def test_simulator_initializes():
    sim = RetailSimulator()
    assert len(sim.demand_generators) > 0

from unittest.mock import patch

@patch("src.simulation.demand_generator.DemandGenerator._try_load_model")
def test_generators_load_models(mock_try_load):
    sim = RetailSimulator()
    for gen in sim.demand_generators.values():
        gen._using_model = True
        assert gen.using_trained_model is True

def test_inject_disruption_viral_trend():
    sim = RetailSimulator()
    sim.inject_disruption("viral_trend", severity="high")
    assert sim.active_demand_multiplier == 4.0

def test_inject_disruption_supplier_delay():
    sim = RetailSimulator()
    sim.inject_disruption("supplier_delay", severity="low")
    for agent in sim.inventory_agents.values():
        assert agent.lead_time == 7

def test_inject_disruption_inventory_loss():
    sim = RetailSimulator()
    original_stock = sum(sim.db_inventory.values())
    sim.inject_disruption("inventory_loss", severity="high")
    new_stock = sum(sim.db_inventory.values())
    assert new_stock < original_stock
