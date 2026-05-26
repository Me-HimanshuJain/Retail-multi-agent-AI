"""CLI entry point for model evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from lightgbm import Booster

from .evaluation import evaluate_forecast
from .training import build_feature_columns, engineer_features, load_m5_bundle, melt_sales_frame, split_train_validation
from .xgboost_model import XGBoostForecaster


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate forecasting models")
    parser.add_argument("--data-dir", required=True, help="Directory containing M5 CSV files")
    parser.add_argument("--model-dir", default="models", help="Directory containing trained artifacts")
    parser.add_argument("--validation-days", type=int, default=28, help="Validation horizon in days")
    parser.add_argument("--optuna-trials", type=int, default=0, help="Number of Optuna trials for LightGBM tuning")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    bundle = load_m5_bundle(Path(args.data_dir))
    model_dir = Path(args.model_dir)
    long_frame = melt_sales_frame(bundle.sales)
    feature_frame = engineer_features(long_frame, bundle.calendar, bundle.prices).dropna(subset=["sales"])
    feature_columns = build_feature_columns(feature_frame)
    train_frame, validation_frame = split_train_validation(feature_frame, validation_days=args.validation_days)
    lgbm_model = Booster(model_file=str(model_dir / "m5_lgbm.bin"))
    xgb_model = XGBoostForecaster.load(model_dir / "m5_xgb.bin")
    lgbm_prediction = lgbm_model.predict(validation_frame[feature_columns])
    xgb_prediction = xgb_model.predict(validation_frame[feature_columns])["median"]
    lgbm_metrics = evaluate_forecast(validation_frame["sales"].to_numpy(), lgbm_prediction)
    xgb_metrics = evaluate_forecast(validation_frame["sales"].to_numpy(), xgb_prediction)
    print({"lgbm": lgbm_metrics, "xgb": xgb_metrics})


if __name__ == "__main__":
    main()
