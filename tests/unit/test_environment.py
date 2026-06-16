import pytest
from src.simulation.environment import RetailSimulator
from unittest.mock import patch

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

def test_environment_demand_generator_fallback():
    # Test lines 225-235 exception catching
    sim = RetailSimulator(seed=42)
    # mock DemandGenerator to raise exception
    with patch("src.simulation.environment.DemandGenerator", side_effect=Exception("mocked error")):
        sim._load_from_rows([{"id": 1, "name": "CA_1"}], [], [])
        assert "CA_1" not in sim.demand_generators

def test_environment_db_flush_exception():
    sim = RetailSimulator(seed=42)
    sim._db_available = True
    sim.db_inventory = {(1, 1): 10}
    with patch("src.core.database.SessionLocal", side_effect=Exception("db error")):
        sim._flush_inventory_to_db() # Should warn but not raise

def test_environment_db_flush_success():
    sim = RetailSimulator(seed=42)
    sim._db_available = True
    sim.db_inventory = {(1, 1): 10}
    mock_session = MagicMock()
    with patch("src.core.database.SessionLocal", return_value=mock_session):
        sim._flush_inventory_to_db()
    mock_session.execute.assert_called()
    mock_session.commit.assert_called()
    mock_session.close.assert_called()
