import pytest
from unittest.mock import patch, MagicMock
from src.models.forecasting.predict import build_parser, main
import pandas as pd

def test_build_parser():
    parser = build_parser()
    args = parser.parse_args(["--data-dir", "data", "--model-dir", "models", "--model", "xgboost"])
    assert args.data_dir == "data"
    assert args.model_dir == "models"
    assert args.model == "xgboost"

@patch("src.models.forecasting.predict.build_parser")
@patch("src.models.forecasting.predict.load_m5_bundle")
@patch("src.models.forecasting.predict.XGBoostForecaster")
@patch("src.models.forecasting.predict.engineer_features")
@patch("src.models.forecasting.predict.build_feature_columns")
@patch("src.models.forecasting.predict.melt_sales_frame")
def test_main_xgboost(mock_melt, mock_build_cols, mock_engineer, mock_xgb, mock_load, mock_parser):
    mock_args = MagicMock()
    mock_args.data_dir = "data"
    mock_args.model_dir = "models"
    mock_args.model = "xgboost"
    mock_parser.return_value.parse_args.return_value = mock_args
    
    mock_bundle = MagicMock()
    mock_load.return_value = mock_bundle
    
    mock_features = pd.DataFrame({"id": ["A", "A"], "d_num": [1, 2], "sales": [10, 20]})
    mock_engineer.return_value = mock_features
    mock_build_cols.return_value = ["d_num"]
    
    mock_model = MagicMock()
    mock_model.predict.return_value = pd.DataFrame({"median": [15]})
    mock_xgb.load.return_value = mock_model
    
    # Run main and ensure no errors
    main()
    mock_xgb.load.assert_called_once()
    mock_model.predict.assert_called_once()

@patch("src.models.forecasting.predict.build_parser")
@patch("src.models.forecasting.predict.load_m5_bundle")
@patch("src.models.forecasting.predict.ProphetForecaster")
def test_main_prophet(mock_prophet, mock_load, mock_parser):
    mock_args = MagicMock()
    mock_args.data_dir = "data"
    mock_args.model_dir = "models"
    mock_args.model = "prophet"
    mock_parser.return_value.parse_args.return_value = mock_args
    
    mock_model = MagicMock()
    mock_model.predict.return_value = pd.DataFrame({"ds": ["2020-01-01"], "yhat": [15]})
    mock_prophet.load.return_value = mock_model
    
    main()
    mock_prophet.load.assert_called_once()
    mock_model.predict.assert_called_once()
