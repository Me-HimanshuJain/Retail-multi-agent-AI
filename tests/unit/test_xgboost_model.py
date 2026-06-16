import pytest
import numpy as np
import pandas as pd
from src.models.forecasting.xgboost_model import XGBoostForecaster

def test_xgb_forecaster_fit_predict():
    forecaster = XGBoostForecaster()
    X = pd.DataFrame({"f1": [1, 2, 3, 4, 5], "f2": [5, 4, 3, 2, 1]})
    y = np.array([1, 2, 3, 4, 5])
    forecaster.fit(X, y)
    assert forecaster.is_fitted
    assert len(forecaster.feature_names) == 2
    
    preds = forecaster.predict(X)
    assert "median" in preds
    assert "p10" in preds
    assert "p90" in preds
    assert len(preds["median"]) == 5

def test_xgb_forecaster_not_fitted_predict():
    forecaster = XGBoostForecaster()
    X = pd.DataFrame({"f1": [1, 2]})
    with pytest.raises(RuntimeError):
        forecaster.predict(X)

def test_xgb_forecaster_feature_importance():
    forecaster = XGBoostForecaster()
    X = pd.DataFrame({"f1": [1, 2, 3, 4, 5], "f2": [5, 4, 3, 2, 1]})
    y = np.array([1, 2, 3, 4, 5])
    forecaster.fit(X, y)
    fi = forecaster.get_feature_importance()
    assert not fi.empty
    assert "feature" in fi.columns

def test_xgb_forecaster_feature_importance_not_fitted():
    forecaster = XGBoostForecaster()
    with pytest.raises(RuntimeError):
        forecaster.get_feature_importance()

def test_xgb_forecaster_save_load(tmp_path):
    forecaster = XGBoostForecaster()
    X = pd.DataFrame({"f1": [1, 2, 3, 4, 5], "f2": [5, 4, 3, 2, 1]})
    y = np.array([1, 2, 3, 4, 5])
    forecaster.fit(X, y)
    
    model_path = tmp_path / "model.pkl"
    forecaster.save(model_path)
    
    loaded = XGBoostForecaster.load(model_path)
    assert loaded.is_fitted
    assert loaded.feature_names == ["f1", "f2"]

def test_xgb_forecaster_save_unfitted(tmp_path):
    forecaster = XGBoostForecaster()
    model_path = tmp_path / "model.pkl"
    with pytest.raises(RuntimeError):
        forecaster.save(model_path)

def test_xgb_forecaster_load_not_found():
    with pytest.raises(FileNotFoundError):
        XGBoostForecaster.load("non_existent_file.bin")
