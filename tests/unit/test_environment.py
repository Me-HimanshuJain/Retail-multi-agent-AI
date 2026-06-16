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
