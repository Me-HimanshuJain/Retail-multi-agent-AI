"""Train a real LightGBM model for M5 store-level forecasting."""

from __future__ import annotations

import argparse
import joblib
import json
import time
from pathlib import Path

import pandas as pd

from .m5_data import filter_store_sales, load_m5_dataset
from .training import (
    build_feature_columns,
    engineer_features,
    melt_sales_frame,
    split_train_validation,
    train_lightgbm_model,
)
from .wrmsse import WRMSSEEvaluator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train LightGBM for M5")
    parser.add_argument("--data-dir", required=True, help="Path to M5 data directory")
    parser.add_argument("--store-id", default="CA_1", help="Store id to train")
    parser.add_argument("--model-path", default="models/lgb_model_CA_1.bin", help="Output model artifact path")
    parser.add_argument("--metrics-path", default="models/lgb_model_CA_1.metrics.json", help="Output metrics path")
    parser.add_argument("--optuna-trials", type=int, default=10, help="Optuna trials")
    parser.add_argument("--validation-days", type=int, default=28, help="Validation horizon")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    start = time.perf_counter()

    dataset = load_m5_dataset(args.data_dir)
    sales = filter_store_sales(dataset, args.store_id)
    long_sales = melt_sales_frame(sales)
    feature_frame = engineer_features(long_sales, dataset.calendar, dataset.sell_prices).dropna(subset=["sales"]) 
    feature_columns = build_feature_columns(feature_frame)
    train_frame, validation_frame = split_train_validation(feature_frame, validation_days=args.validation_days)

    model, metrics = train_lightgbm_model(
        train_frame,
        validation_frame,
        feature_columns,
        n_trials=args.optuna_trials,
    )
    model_path = Path(args.model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    # Save as joblib Booster (consistent with existing .bin artifacts in models/)
    joblib.dump(model.booster_, model_path)

    wrmsse = WRMSSEEvaluator(train_long=long_sales, weights=dataset.weights_validation)
    pred_long = validation_frame[["id", "d_num"]].copy()
    pred_long["sales"] = model.predict(validation_frame[feature_columns])
    actual_long = validation_frame[["id", "d_num", "sales"]].copy()
    metrics["wrmsse"] = wrmsse.score(actual_long=actual_long, predicted_long=pred_long)
    metrics["training_time_sec"] = time.perf_counter() - start

    metrics_path = Path(args.metrics_path)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
