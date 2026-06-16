import sys
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
import pandas as pd

@patch("src.models.forecasting.train.train_forecasting_workflow")
def test_train_main(mock_wf):
    from src.models.forecasting.train import main
    with patch.object(sys, 'argv', ["train.py", "--data-dir", "fake_dir"]):
        mock_wf.return_value = {"test": {"metric": 1.0}}
        main()
        mock_wf.assert_called_once()

@patch("src.models.forecasting.train_lgbm.train_lightgbm_model")
@patch("src.models.forecasting.train_lgbm.split_train_validation")
@patch("src.models.forecasting.train_lgbm.build_feature_columns")
@patch("src.models.forecasting.train_lgbm.engineer_features")
@patch("src.models.forecasting.train_lgbm.melt_sales_frame")
@patch("src.models.forecasting.train_lgbm.filter_store_sales")
@patch("src.models.forecasting.train_lgbm.load_m5_dataset")
@patch("src.models.forecasting.train_lgbm.WRMSSEEvaluator")
@patch("joblib.dump")
def test_train_lgbm_main(mock_dump, mock_wrmsse, mock_load, mock_filter, mock_melt, mock_eng, mock_build, mock_split, mock_train, tmp_path):
    from src.models.forecasting.train_lgbm import main
    metrics_file = tmp_path / "metrics.json"
    with patch.object(sys, 'argv', ["train_lgbm.py", "--data-dir", "fake_dir", "--metrics-path", str(metrics_file)]):
        mock_train.return_value = (MagicMock(), {"rmse": 1.0})
        mock_split.return_value = (pd.DataFrame(), pd.DataFrame({"id": [1], "d_num": [1], "sales": [1]}))
        mock_wrmsse.return_value.score.return_value = 1.0
        main()
        mock_train.assert_called_once()

@patch("src.models.forecasting.train_xgboost.train_xgboost_model")
@patch("src.models.forecasting.train_xgboost.split_train_validation")
@patch("src.models.forecasting.train_xgboost.build_feature_columns")
@patch("src.models.forecasting.train_xgboost.engineer_features")
@patch("src.models.forecasting.train_xgboost.melt_sales_frame")
@patch("src.models.forecasting.train_xgboost.filter_store_sales")
@patch("src.models.forecasting.train_xgboost.load_m5_dataset")
@patch("src.models.forecasting.train_xgboost.WRMSSEEvaluator")
def test_train_xgboost_main(mock_wrmsse, mock_load, mock_filter, mock_melt, mock_eng, mock_build, mock_split, mock_train, tmp_path):
    from src.models.forecasting.train_xgboost import main
    metrics_file = tmp_path / "metrics.json"
    with patch.object(sys, 'argv', ["train_xgboost.py", "--data-dir", "fake_dir", "--metrics-path", str(metrics_file)]):
        mock_train.return_value = (MagicMock(), {"rmse": 1.0})
        mock_split.return_value = (pd.DataFrame(), pd.DataFrame({"id": [1], "d_num": [1], "sales": [1]}))
        mock_wrmsse.return_value.score.return_value = 1.0
        main()
        mock_train.assert_called_once()

@patch("src.models.forecasting.train_ensemble.load_lgbm_booster")
@patch("src.models.forecasting.train_ensemble.XGBoostForecaster")
@patch("src.models.forecasting.train_ensemble.split_train_validation")
@patch("src.models.forecasting.train_ensemble.build_feature_columns")
@patch("src.models.forecasting.train_ensemble.engineer_features")
@patch("src.models.forecasting.train_ensemble.melt_sales_frame")
@patch("src.models.forecasting.train_ensemble.filter_store_sales")
@patch("src.models.forecasting.train_ensemble.load_m5_dataset")
@patch("src.models.forecasting.train_ensemble.WRMSSEEvaluator")
@patch("src.models.forecasting.train_ensemble.ForecastEnsemble")
@patch("scipy.optimize.minimize")
def test_train_ensemble_main(mock_minimize, mock_ensemble, mock_wrmsse, mock_load, mock_filter, mock_melt, mock_eng, mock_build, mock_split, mock_xgb, mock_lgbm, tmp_path):
    from src.models.forecasting.train_ensemble import main
    metrics_file = tmp_path / "metrics.json"
    with patch.object(sys, 'argv', ["train_ensemble.py", "--data-dir", "fake_dir", "--metrics-path", str(metrics_file)]):
        mock_split.return_value = (pd.DataFrame(), pd.DataFrame({"id": [1], "d_num": [1], "sales": [1]}))
        mock_lgbm.return_value.predict.return_value = [1]
        mock_xgb.load.return_value.predict.return_value = pd.DataFrame({"median": [1]})
        mock_minimize.return_value.success = True
        mock_minimize.return_value.x = np.array([0.6, 0.4])
        mock_wrmsse.return_value.score.return_value = 1.0
        main()
        mock_ensemble.assert_called_once()
