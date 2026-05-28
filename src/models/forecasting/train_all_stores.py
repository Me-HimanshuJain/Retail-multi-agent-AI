"""Train LightGBM models for all target stores and generate a comparison report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


TARGET_STORES = [
    "CA_2",
    "CA_3",
    "CA_4",
    "TX_1",
    "TX_2",
    "TX_3",
    "WI_1",
    "WI_2",
    "WI_3",
]

METRIC_COLUMNS = ["rmse", "mae", "mape", "wrmsse", "training_time_sec"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train all stores and generate comparison report")
    parser.add_argument("--data-dir", default="data", help="Path to M5 data directory")
    parser.add_argument("--models-dir", default="models", help="Output models directory")
    parser.add_argument("--report-path", default="STORE_COMPARISON_REPORT.md", help="Markdown report output path")
    parser.add_argument("--optuna-trials", type=int, default=2, help="Optuna trials for each store")
    parser.add_argument("--validation-days", type=int, default=7, help="Validation horizon")
    return parser


def _run_store_training(
    store_id: str,
    data_dir: str,
    models_dir: Path,
    optuna_trials: int,
    validation_days: int,
) -> Path:
    model_path = models_dir / f"lgb_model_{store_id}.bin"
    metrics_path = models_dir / f"lgb_model_{store_id}.metrics.json"
    cmd = [
        sys.executable,
        "-m",
        "src.models.forecasting.train_lgbm",
        "--data-dir",
        data_dir,
        "--store-id",
        store_id,
        "--model-path",
        str(model_path),
        "--metrics-path",
        str(metrics_path),
        "--optuna-trials",
        str(optuna_trials),
        "--validation-days",
        str(validation_days),
    ]
    subprocess.run(cmd, check=True)
    return metrics_path


def _load_metrics(store_id: str, metrics_path: Path) -> dict[str, float | str]:
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    row: dict[str, float | str] = {"store_id": store_id}
    for column in METRIC_COLUMNS:
        row[column] = float(payload[column])
    return row


def _generate_plots(summary: pd.DataFrame, models_dir: Path) -> dict[str, Path]:
    plot_paths = {
        "rmse": models_dir / "store_rmse_comparison.png",
        "mae": models_dir / "store_mae_comparison.png",
        "mape": models_dir / "store_mape_comparison.png",
        "wrmsse": models_dir / "store_wrmsse_comparison.png",
        "duration": models_dir / "store_training_duration_comparison.png",
    }

    ordered = summary.sort_values("overall_rank").copy()
    ordered["store_label"] = ordered["store_id"]

    charts = [
        ("rmse", "RMSE", plot_paths["rmse"]),
        ("mae", "MAE", plot_paths["mae"]),
        ("mape", "MAPE", plot_paths["mape"]),
        ("wrmsse", "WRMSSE", plot_paths["wrmsse"]),
        ("training_time_sec", "Training Duration (sec)", plot_paths["duration"]),
    ]

    for metric_column, title, output_path in charts:
        plt.figure(figsize=(10, 5))
        plt.bar(ordered["store_label"], ordered[metric_column])
        plt.title(f"Store Comparison: {title}")
        plt.xlabel("Store")
        plt.ylabel(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()

    return plot_paths


def _build_summary(metrics_rows: list[dict[str, float | str]]) -> pd.DataFrame:
    summary = pd.DataFrame(metrics_rows)
    summary["rank_rmse"] = summary["rmse"].rank(method="min", ascending=True)
    summary["rank_mae"] = summary["mae"].rank(method="min", ascending=True)
    summary["rank_mape"] = summary["mape"].rank(method="min", ascending=True)
    summary["rank_wrmsse"] = summary["wrmsse"].rank(method="min", ascending=True)
    summary["rank_duration"] = summary["training_time_sec"].rank(method="min", ascending=True)
    summary["overall_rank"] = (
        summary[["rank_rmse", "rank_mae", "rank_mape", "rank_wrmsse", "rank_duration"]].mean(axis=1)
    )
    summary = summary.sort_values("overall_rank").reset_index(drop=True)
    summary["store_ranking"] = summary.index + 1
    return summary


def _format_markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    table = frame[columns].copy()
    return table.to_markdown(index=False)


def _write_report(report_path: Path, summary: pd.DataFrame, plot_paths: dict[str, Path], elapsed_sec: float) -> None:
    top = summary.iloc[0]
    report = [
        "# Store Comparison Report",
        "",
        "## Scope",
        "",
        "- Trained LightGBM artifacts for: CA_2, CA_3, CA_4, TX_1, TX_2, TX_3, WI_1, WI_2, WI_3.",
        "- Evaluated with RMSE, MAE, MAPE, WRMSSE, and training duration.",
        f"- Total orchestration time (seconds): `{elapsed_sec:.2f}`",
        "",
        "## Store Ranking",
        "",
        f"- Top-ranked store: `{top['store_id']}`",
        f"- Top-ranked average rank score: `{float(top['overall_rank']):.2f}`",
        "",
        _format_markdown_table(
            summary,
            [
                "store_ranking",
                "store_id",
                "rmse",
                "mae",
                "mape",
                "wrmsse",
                "training_time_sec",
                "overall_rank",
            ],
        ),
        "",
        "## Plot Artifacts",
        "",
        f"- RMSE comparison: `{plot_paths['rmse'].as_posix()}`",
        f"- MAE comparison: `{plot_paths['mae'].as_posix()}`",
        f"- MAPE comparison: `{plot_paths['mape'].as_posix()}`",
        f"- WRMSSE comparison: `{plot_paths['wrmsse'].as_posix()}`",
        f"- Training duration comparison: `{plot_paths['duration'].as_posix()}`",
        "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    started = time.perf_counter()
    models_dir = Path(args.models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows: list[dict[str, float | str]] = []
    for store_id in TARGET_STORES:
        metrics_path = _run_store_training(
            store_id=store_id,
            data_dir=args.data_dir,
            models_dir=models_dir,
            optuna_trials=args.optuna_trials,
            validation_days=args.validation_days,
        )
        metrics_rows.append(_load_metrics(store_id=store_id, metrics_path=metrics_path))

    summary = _build_summary(metrics_rows)
    summary_csv = models_dir / "store_comparison_metrics.csv"
    summary.to_csv(summary_csv, index=False)

    plot_paths = _generate_plots(summary=summary, models_dir=models_dir)
    _write_report(
        report_path=Path(args.report_path),
        summary=summary,
        plot_paths=plot_paths,
        elapsed_sec=time.perf_counter() - started,
    )
    print(summary[["store_ranking", "store_id", "rmse", "mae", "mape", "wrmsse", "training_time_sec"]].to_string(index=False))


if __name__ == "__main__":
    main()