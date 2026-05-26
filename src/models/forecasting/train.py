"""CLI entry point for real forecasting model training."""

from __future__ import annotations

import argparse
from pathlib import Path

from .training import train_forecasting_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the M5 forecasting models")
    parser.add_argument("--data-dir", required=True, help="Directory containing M5 CSV files")
    parser.add_argument("--model-dir", default="models", help="Directory to write trained artifacts")
    parser.add_argument("--validation-days", type=int, default=28, help="Validation horizon in days")
    parser.add_argument("--optuna-trials", type=int, default=0, help="Number of Optuna trials for LightGBM tuning")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    metrics = train_forecasting_workflow(
        data_dir=Path(args.data_dir),
        model_dir=Path(args.model_dir),
        validation_days=args.validation_days,
        n_trials=args.optuna_trials,
    )
    for model_name, metric_values in metrics.items():
        print(model_name, metric_values)


if __name__ == "__main__":
    main()
