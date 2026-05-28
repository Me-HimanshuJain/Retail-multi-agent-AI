"""Train weighted ensemble using LightGBM and XGBoost validation predictions."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np

from .ensemble import ForecastEnsemble
from .m5_data import filter_store_sales, load_m5_dataset
from .training import build_feature_columns, engineer_features, melt_sales_frame, split_train_validation
from .wrmsse import WRMSSEEvaluator
from .xgboost_model import XGBoostForecaster


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train weighted ensemble using WRMSSE optimization")
    parser.add_argument("--data-dir", required=True, help="Path to M5 data directory")
    parser.add_argument("--store-id", default="CA_1", help="Store id to evaluate")
    parser.add_argument("--lgbm-model", default="models/lgb_model_CA_1.bin", help="Path to LGBM booster")
    parser.add_argument("--xgb-model", default="models/xgb_model_CA_1.bin", help="Path to XGB artifact")
    parser.add_argument("--ensemble-model", default="models/ensemble_CA_1.bin", help="Output ensemble path")
    parser.add_argument("--metrics-path", default="models/ensemble_CA_1.metrics.json", help="Output metrics path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    start = time.perf_counter()
    
    dataset = load_m5_dataset(args.data_dir)
    sales = filter_store_sales(dataset, args.store_id)
    long_sales = melt_sales_frame(sales)
    feature_frame = engineer_features(long_sales, dataset.calendar, dataset.sell_prices).dropna(subset=["sales"]) 
    feature_columns = build_feature_columns(feature_frame)
    _, validation_frame = split_train_validation(feature_frame, validation_days=28)

    # Load trained models
    lgbm = lgb.Booster(model_file=str(Path(args.lgbm_model)))
    xgb = XGBoostForecaster.load(Path(args.xgb_model))

    # Generate validation predictions
    val = validation_frame[["id", "d_num", "sales"]].copy()
    val["lgbm_pred"] = lgbm.predict(validation_frame[feature_columns])
    val["xgb_pred"] = xgb.predict(validation_frame[feature_columns])["median"]
    
    # Create ensemble
    ensemble = ForecastEnsemble(models={"lgbm": lgbm, "xgb": xgb})
    
    # Optimize weights using WRMSSE metric
    wrmsse_eval = WRMSSEEvaluator(train_long=long_sales, weights=dataset.weights_validation)
    
    # Create validation sets in long format for WRMSSE calculation
    val_actual_long = val[["id", "d_num", "sales"]].copy()
    val_actual_long = val_actual_long.rename(columns={"sales": "sales"})
    
    # Optimize weights to minimize WRMSSE
    from scipy.optimize import minimize
    
    def objective_wrmsse(weight_vector: np.ndarray) -> float:
        w = weight_vector / weight_vector.sum()  # Normalize weights
        ensemble_pred = w[0] * val["lgbm_pred"].values + w[1] * val["xgb_pred"].values
        
        val_pred_long = val[["id", "d_num"]].copy()
        val_pred_long["sales"] = ensemble_pred
        
        score = wrmsse_eval.score(actual_long=val_actual_long, predicted_long=val_pred_long)
        return float(score)
    
    # Optimize weights
    x0 = np.array([0.5, 0.5])
    bounds = [(0.01, 0.99), (0.01, 0.99)]
    result = minimize(objective_wrmsse, x0, bounds=bounds, method="L-BFGS-B")
    
    if result.success:
        optimized_weights = result.x / result.x.sum()
        ensemble.weights = {"lgbm": float(optimized_weights[0]), "xgb": float(optimized_weights[1])}
    else:
        ensemble.weights = {"lgbm": 0.5, "xgb": 0.5}
    
    # Save ensemble
    ensemble.save(Path(args.ensemble_model))

    # Calculate metrics for each model
    metrics = {}
    
    # Individual model WRMSSE scores
    val_lgbm_long = val[["id", "d_num"]].copy()
    val_lgbm_long["sales"] = val["lgbm_pred"]
    lgbm_wrmsse = wrmsse_eval.score(actual_long=val_actual_long, predicted_long=val_lgbm_long)
    
    val_xgb_long = val[["id", "d_num"]].copy()
    val_xgb_long["sales"] = val["xgb_pred"]
    xgb_wrmsse = wrmsse_eval.score(actual_long=val_actual_long, predicted_long=val_xgb_long)
    
    # Ensemble WRMSSE score
    ensemble_pred = ensemble.weights["lgbm"] * val["lgbm_pred"].values + ensemble.weights["xgb"] * val["xgb_pred"].values
    val_ensemble_long = val[["id", "d_num"]].copy()
    val_ensemble_long["sales"] = ensemble_pred
    ensemble_wrmsse = wrmsse_eval.score(actual_long=val_actual_long, predicted_long=val_ensemble_long)
    
    metrics["lgbm_wrmsse"] = float(lgbm_wrmsse)
    metrics["xgb_wrmsse"] = float(xgb_wrmsse)
    metrics["ensemble_wrmsse"] = float(ensemble_wrmsse)
    metrics["weights"] = ensemble.weights
    metrics["training_time_sec"] = time.perf_counter() - start
    
    Path(args.metrics_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.metrics_path).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
