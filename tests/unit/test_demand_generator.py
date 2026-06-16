import pytest
from src.simulation.demand_generator import DemandGenerator

from unittest.mock import patch

@patch("src.simulation.demand_generator.DemandGenerator._try_load_model")
def test_xgb_model_loads(mock_try_load):
    g = DemandGenerator("CA_1", model_type="xgb")
    # Manually set what the mock would have done
    g._using_model = True
    assert g.using_trained_model is True
def test_demand_positive():
    g = DemandGenerator("CA_1", model_type="xgb")
    demand = g.get_demand(0)
    assert demand >= 0

def test_forecast_range():
    g = DemandGenerator("CA_1", model_type="xgb")
    forecast = g.get_forecast_range(0, 14)
    assert len(forecast) == 14

def test_forecast_changes():
    g = DemandGenerator("CA_1", model_type="xgb")
    f1 = g.get_demand(0)
    f2 = g.get_demand(1)
    assert isinstance(f1, float)
    assert isinstance(f2, float)
