import pytest
import numpy as np
import pandas as pd
from src.models.forecasting.ensemble import ForecastEnsemble

def test_ensemble_add_model():
    ensemble = ForecastEnsemble()
    ensemble.add_model("m1", "model1")
    assert "m1" in ensemble.models

def test_ensemble_fit_weights():
    ensemble = ForecastEnsemble()
    df = pd.DataFrame({"actual": [1, 2, 3], "m1": [1, 1.9, 3.1], "m2": [0.5, 1.5, 2.5]})
    weights = ensemble.fit_weights(df)
    assert "m1" in weights
    assert "m2" in weights
    assert np.isclose(weights["m1"] + weights["m2"], 1.0)

def test_ensemble_fit_weights_no_models():
    ensemble = ForecastEnsemble()
    df = pd.DataFrame({"actual": [1, 2, 3]})
    with pytest.raises(ValueError):
        ensemble.fit_weights(df)

def test_ensemble_combine():
    ensemble = ForecastEnsemble(weights={"m1": 0.8, "m2": 0.2})
    forecasts = {"m1": np.array([1.0, 2.0]), "m2": np.array([2.0, 3.0])}
    result = ensemble.combine(forecasts)
    assert "median" in result
    assert "p10" in result
    assert "p90" in result
    assert np.allclose(result["median"], [1.2, 2.2])

def test_ensemble_combine_empty():
    ensemble = ForecastEnsemble()
    with pytest.raises(ValueError):
        ensemble.combine({})

def test_ensemble_combine_mismatch_horizon():
    ensemble = ForecastEnsemble()
    forecasts = {"m1": np.array([1.0]), "m2": np.array([1.0, 2.0])}
    with pytest.raises(ValueError):
        ensemble.combine(forecasts)

def test_ensemble_combine_no_weights():
    ensemble = ForecastEnsemble()
    forecasts = {"m1": np.array([1.0, 2.0]), "m2": np.array([2.0, 3.0])}
    result = ensemble.combine(forecasts)
    assert np.allclose(result["median"], [1.5, 2.5])

def test_ensemble_forecast():
    ensemble = ForecastEnsemble(weights={"m1": 0.5, "m2": 0.5})
    forecasts = {"m1": np.array([1.0]), "m2": np.array([3.0])}
    res = ensemble.forecast(forecasts)
    assert np.allclose(res["median"], [2.0])

def test_ensemble_forecast_with_uncertainty():
    ensemble = ForecastEnsemble(weights={"m1": 0.5, "m2": 0.5})
    forecasts = {"m1": np.array([1.0]), "m2": np.array([3.0])}
    med, p10, p90 = ensemble.forecast_with_uncertainty(forecasts)
    assert len(med) == 1
    assert len(p10) == 1
    assert len(p90) == 1

def test_ensemble_evaluate_all():
    ensemble = ForecastEnsemble()
    df = pd.DataFrame({"actual": [1, 2], "m1": [1, 2], "m2": [2, 3]})
    metrics = ensemble.evaluate_all(df)
    assert metrics["m1"] == 0.0
    assert metrics["m2"] == 1.0

def test_ensemble_evaluate_all_missing_actual():
    ensemble = ForecastEnsemble()
    df = pd.DataFrame({"m1": [1, 2]})
    with pytest.raises(ValueError):
        ensemble.evaluate_all(df)

def test_ensemble_get_model_status():
    ensemble = ForecastEnsemble(models={"m1": "model1"})
    status = ensemble.get_model_status()
    assert len(status) == 1
    assert status[0]["name"] == "m1"
    assert status[0]["status"] == "trained"

def test_ensemble_save_load(tmp_path):
    ensemble = ForecastEnsemble(models={"m1": "model"}, weights={"m1": 1.0})
    path = tmp_path / "ens.pkl"
    ensemble.save(path)
    loaded = ForecastEnsemble.load(path)
    assert loaded.weights["m1"] == 1.0
    assert loaded.models["m1"] == "model"
