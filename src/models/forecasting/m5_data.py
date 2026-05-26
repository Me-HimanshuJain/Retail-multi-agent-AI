"""M5 dataset loading and preprocessing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class M5Dataset:
    calendar: pd.DataFrame
    sell_prices: pd.DataFrame
    sales_train_validation: pd.DataFrame
    weights_validation: pd.DataFrame | None


def load_m5_dataset(data_dir: str | Path) -> M5Dataset:
    base = Path(data_dir)
    calendar = pd.read_csv(base / "calendar.csv")
    sell_prices = pd.read_csv(base / "sell_prices.csv")
    sales_train_validation = pd.read_csv(base / "sales_train_validation.csv")
    weights_path = base / "weights_validation.csv"
    weights_validation = pd.read_csv(weights_path) if weights_path.exists() else None
    return M5Dataset(
        calendar=calendar,
        sell_prices=sell_prices,
        sales_train_validation=sales_train_validation,
        weights_validation=weights_validation,
    )


def filter_store_sales(dataset: M5Dataset, store_id: str) -> pd.DataFrame:
    frame = dataset.sales_train_validation.copy()
    if "store_id" not in frame.columns:
        raise ValueError("sales_train_validation.csv must contain store_id")
    return frame[frame["store_id"] == store_id].copy()
