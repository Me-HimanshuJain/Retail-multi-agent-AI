"""Train weighted ensemble using LightGBM and XGBoost validation predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb

from .ensemble import ForecastEnsemble
from .m5_data import filter_store_sales, load_m5_dataset
from .training import build_feature_columns, engineer_features, melt_sales_frame, split_train_validation
from .xgboost_model import XGBoostForecaster


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train weighted ensemble")
    parser.add_argument("--data-dir", required=True, help="Path to M5 data directory")
    parser.add_argument("--store-id", default="CA_1", help="Store id to evaluate")
    parser.add_argument("--lgbm-model", default="models/lgb_model_CA_1.bin", help="Path to LGBM booster")
    parser.add_argument("--xgb-model", default="models/xgb_model_CA_1.bin", help="Path to XGB artifact")
    parser.add_argument("--ensemble-model", default="models/ensemble_CA_1.bin", help="Output ensemble path")
    parser.add_argument("--metrics-path", default="models/ensemble_CA_1.metrics.json", help="Output metrics path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    dataset = load_m5_dataset(args.data_dir)
    sales = filter_store_sales(dataset, args.store_id)
    long_sales = melt_sales_frame(sales)
    feature_frame = engineer_features(long_sales, dataset.calendar, dataset.sell_prices).dropna(subset=["sales"]) 
    feature_columns = build_feature_columns(feature_frame)
    _, validation_frame = split_train_validation(feature_frame, validation_days=28)

    lgbm = lgb.Booster(model_file=str(Path(args.lgbm_model)))
    xgb = XGBoostForecaster.load(Path(args.xgb_model))

    val = validation_frame[["sales"]].copy()
    val["lgbm"] = lgbm.predict(validation_frame[feature_columns])
    val["xgb"] = xgb.predict(validation_frame[feature_columns])["median"]
    val = val.rename(columns={"sales": "actual"})

    ensemble = ForecastEnsemble(models={"lgbm": lgbm, "xgb": xgb})
    weights = ensemble.fit_weights(val[["actual", "lgbm", "xgb"]], actual_col="actual")
    ensemble.save(Path(args.ensemble_model))

    metrics = ensemble.evaluate_all(val[["actual", "lgbm", "xgb"]], actual_col="actual")
    metrics["weights"] = weights
    Path(args.metrics_path).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
