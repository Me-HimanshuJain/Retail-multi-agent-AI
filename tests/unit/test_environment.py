import pytest
from src.simulation.environment import RetailSimulator

def test_simulator_initializes():
    sim = RetailSimulator()
    assert len(sim.demand_generators) > 0

def test_generators_load_models():
    sim = RetailSimulator()
    for gen in sim.demand_generators.values():
        assert gen.using_trained_model is True
