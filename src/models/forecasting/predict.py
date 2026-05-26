"""CLI entry point for trained forecasting inference."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .prophet_model import ProphetForecaster
from .training import load_m5_bundle, engineer_features, melt_sales_frame, build_feature_columns
from .xgboost_model import XGBoostForecaster


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate forecasts using trained artifacts")
    parser.add_argument("--data-dir", required=True, help="Directory containing M5 CSV files")
    parser.add_argument("--model-dir", default="models", help="Directory containing saved artifacts")
    parser.add_argument("--model", choices=["xgboost", "prophet"], default="xgboost", help="Which trained model to load")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    bundle = load_m5_bundle(Path(args.data_dir))
    model_dir = Path(args.model_dir)

    if args.model == "xgboost":
        model = XGBoostForecaster.load(model_dir / "m5_xgb.bin")
        long_frame = melt_sales_frame(bundle.sales)
        feature_frame = engineer_features(long_frame, bundle.calendar, bundle.prices).dropna(subset=["sales"])
        feature_columns = build_feature_columns(feature_frame)
        latest_rows = feature_frame.sort_values(["id", "d_num"]).groupby("id").tail(1)
        predictions = model.predict(latest_rows[feature_columns])
        output = latest_rows[["id", "d_num"]].copy()
        output["forecast"] = predictions["median"]
        print(output.head())
    else:
        model = ProphetForecaster.load(model_dir / "m5_prophet.bin")
        forecast = model.predict(periods=28)
        print(forecast.head())


if __name__ == "__main__":
    main()
