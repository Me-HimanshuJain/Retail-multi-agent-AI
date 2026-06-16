import pytest
from src.simulation.environment import RetailSimulator
from unittest.mock import patch, MagicMock

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

def test_load_from_rows_success():
    sim = RetailSimulator(seed=42)
    stores = [{"id": 1, "name": "CA_1"}]
    products = [{"id": 100, "base_price": 2.5, "unit_cost": 1.0, "shelf_life_days": 10}]
    inventory = [{"location_id": 1, "product_id": 100, "quantity": 50}]
    
    with patch("src.simulation.environment.DemandGenerator"):
        sim._load_from_rows(stores, products, inventory)
        
    assert sim.product_prices[100] == 2.5
    assert sim.product_costs[100] == 1.0
    assert sim.product_shelf_life[100] == 10
    assert sim.store_names[1] == "CA_1"
    assert sim.db_inventory[(1, 100)] == 50
    assert (1, 100) in sim.inventory_agents

@pytest.mark.asyncio
async def test_run_simulation_and_metrics():
    sim = RetailSimulator(seed=42)
    # mock demand_generators
    mock_gen = MagicMock()
    mock_gen.get_demand.return_value = 10.0
    sim.demand_generators = {1: mock_gen}
    sim.db_inventory = {(1, 100): 5}
    sim.product_prices = {100: 2.0}
    sim.product_costs = {100: 1.0}
    sim.product_shelf_life = {100: 30}
    mock_agent = MagicMock()
    mock_agent.step.return_value = (0, 0)
    sim.inventory_agents = {(1, 100): mock_agent}
    sim._db_available = True
    
    with patch("src.simulation.environment.RetailSimulator._flush_inventory_to_db"):
        metrics = await sim.run(days=2)
        assert "total_revenue" in metrics

def test_simulator_start_date_string():
    sim = RetailSimulator(start_date="2020-01-01T00:00:00")
    assert sim.start_date.year == 2020

@patch("src.simulation.environment.DemandGenerator", side_effect=Exception("DemandGenerator fallback crash"))
def test_simulator_load_fallback_exception(mock_dg):
    sim = RetailSimulator()
    # Ensure it doesn't crash the constructor and prints a warning
    assert len(sim.demand_generators) == 0

@pytest.mark.asyncio
async def test_run_simulation_viral_trend_decay():
    sim = RetailSimulator()
    sim.inject_disruption("viral_trend", "high")
    assert sim.active_demand_multiplier == 4.0
    with patch("src.simulation.environment.RetailSimulator._flush_inventory_to_db"):
        await sim.run(days=1)
    assert sim.active_demand_multiplier == 3.85

@pytest.mark.asyncio
async def test_run_simulation_no_generator():
    sim = RetailSimulator()
    # Remove generators so it hits demand_raw = 5.0
    sim.demand_generators = {}
    with patch("src.simulation.environment.RetailSimulator._flush_inventory_to_db"):
        metrics = await sim.run(days=1)
    assert "total_revenue" in metrics

def test_flush_inventory_exception():
    sim = RetailSimulator()
    sim.db_inventory = {(1, 100): 10}
    sim._db_available = True
    
    # Mock db to raise Exception on commit
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("DB error")
    with patch("src.core.database.SessionLocal", return_value=mock_db):
        # We expect _flush_inventory_to_db to catch it and emit a warning
        sim._flush_inventory_to_db()
        mock_db.rollback.assert_called_once()

def test_smart_agent_none_generator():
    from src.simulation.environment import SmartInventoryAgent
    agent = SmartInventoryAgent()
    arrived, ordered = agent.step(0, 10.0, None)
    assert arrived == 0
    assert ordered == 0

def test_smart_agent_order_qty_min():
    from src.simulation.environment import SmartInventoryAgent
    agent = SmartInventoryAgent()
    mock_gen = MagicMock()
    mock_gen.get_forecast_range.return_value = [1]*17
    # effective inventory is 0, reorder point is 3 (lead time) + safety_stock (0)
    # order_up_to is 14. order_qty = 14 -> bump to 15
    arrived, ordered = agent.step(0, 0, mock_gen)
    assert ordered == 15
    sim = RetailSimulator()
    assert len(sim.get_daily_metrics()) == 0
