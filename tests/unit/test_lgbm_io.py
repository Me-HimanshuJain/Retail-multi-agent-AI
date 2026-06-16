import pytest
import pandas as pd
import joblib
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.models.forecasting.lgbm_io import load_lgbm_booster, align_features_to_model, align_features_to_xgb

def test_load_lgbm_booster_not_found():
    with pytest.raises(FileNotFoundError):
        load_lgbm_booster("non_existent_file.bin")

def test_load_lgbm_booster_value_error(tmp_path):
    p = tmp_path / "bad.bin"
    joblib.dump({"not_a_booster": 1}, p)
    with pytest.raises(ValueError):
        load_lgbm_booster(p)

def test_align_features_to_model():
    df = pd.DataFrame({"day": [1], "sell_price_max": [2], "extra": [3]})
    booster = MagicMock()
    booster.feature_name.return_value = ["mday", "price_max"]
    
    aligned = align_features_to_model(df, booster)
    assert list(aligned.columns) == ["mday", "price_max"]
    assert aligned["mday"].iloc[0] == 1
    assert aligned["price_max"].iloc[0] == 2

def test_align_features_to_model_missing():
    df = pd.DataFrame({"day": [1]})
    booster = MagicMock()
    booster.feature_name.return_value = ["mday", "price_max"]
    with pytest.raises(KeyError):
        align_features_to_model(df, booster)

def test_align_features_to_xgb():
    df = pd.DataFrame({
        "day": [1], "sell_price_max": [2], "wday": [6], "snap_CA": [1],
        "event_name_1": [1], "event_type_1": [0]
    })
    feature_names = [
        "mday", "price_max", "is_weekend", "is_snap", "is_event_1",
        "event_type_cultural", "lag_21"
    ]
    aligned = align_features_to_xgb(df, feature_names)
    assert list(aligned.columns) == feature_names
    assert aligned["mday"].iloc[0] == 1
    assert aligned["price_max"].iloc[0] == 2
    assert aligned["is_weekend"].iloc[0] == 1.0
    assert aligned["is_snap"].iloc[0] == 1.0
    assert aligned["is_event_1"].iloc[0] == 1.0
    assert aligned["event_type_cultural"].iloc[0] == 1.0
    assert aligned["lag_21"].iloc[0] == 0.0
