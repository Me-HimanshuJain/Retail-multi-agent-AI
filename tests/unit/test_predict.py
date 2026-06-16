from unittest.mock import patch, MagicMock
import pandas as pd
from src.models.forecasting.predict import build_parser, main
import pytest

def test_build_parser():
    parser = build_parser()
    args = parser.parse_args(["--data-dir", "dummy_dir", "--model", "xgboost"])
    assert args.data_dir == "dummy_dir"
    assert args.model == "xgboost"

@patch("src.models.forecasting.predict.build_parser")
@patch("src.models.forecasting.predict.load_m5_bundle")
@patch("src.models.forecasting.predict.XGBoostForecaster")
@patch("src.models.forecasting.predict.melt_sales_frame")
@patch("src.models.forecasting.predict.engineer_features")
@patch("src.models.forecasting.predict.build_feature_columns")
def test_main_xgboost(mock_build_cols, mock_eng_feat, mock_melt, mock_xgb, mock_load_bundle, mock_parser):
    mock_args = MagicMock()
    mock_args.data_dir = "dummy_data"
    mock_args.model_dir = "dummy_models"
    mock_args.model = "xgboost"
    mock_parser.return_value.parse_args.return_value = mock_args

    # Mock the bundle
    mock_bundle = MagicMock()
    mock_bundle.sales = pd.DataFrame({"id": ["1"], "sales": [1]})
    mock_load_bundle.return_value = mock_bundle

    # Mock feature frame and predict output
    dummy_features = pd.DataFrame({"id": ["1"], "d_num": [1], "sales": [10], "feature_1": [0.5]})
    mock_eng_feat.return_value = dummy_features
    mock_build_cols.return_value = ["feature_1"]

    mock_model_instance = MagicMock()
    mock_model_instance.predict.return_value = pd.DataFrame({"median": [100.0]})
    mock_xgb.load.return_value = mock_model_instance

    main()
    
    mock_xgb.load.assert_called_once()
    mock_model_instance.predict.assert_called_once()

@patch("src.models.forecasting.predict.build_parser")
@patch("src.models.forecasting.predict.load_m5_bundle")
@patch("src.models.forecasting.predict.ProphetForecaster")
def test_main_prophet(mock_prophet, mock_load_bundle, mock_parser):
    mock_args = MagicMock()
    mock_args.data_dir = "dummy_data"
    mock_args.model_dir = "dummy_models"
    mock_args.model = "prophet"
    mock_parser.return_value.parse_args.return_value = mock_args

    # Mock the model
    mock_model_instance = MagicMock()
    mock_model_instance.predict.return_value = pd.DataFrame({"ds": ["2020-01-01"], "yhat": [100.0]})
    mock_prophet.load.return_value = mock_model_instance

    main()
    
    mock_prophet.load.assert_called_once()
    mock_model_instance.predict.assert_called_once_with(periods=28)
