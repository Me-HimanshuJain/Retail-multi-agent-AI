from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from src.models.forecasting.m5_data import load_m5_dataset, filter_store_sales, M5Dataset

def test_load_m5_dataset_success(tmp_path):
    # Create dummy CSVs
    sales_path = tmp_path / "sales_train_validation.csv"
    calendar_path = tmp_path / "calendar.csv"
    prices_path = tmp_path / "sell_prices.csv"

    pd.DataFrame({"id": ["A"], "item_id": ["item_1"]}).to_csv(sales_path, index=False)
    pd.DataFrame({"date": ["2020-01-01"], "d": ["d_1"]}).to_csv(calendar_path, index=False)
    pd.DataFrame({"store_id": ["CA_1"], "item_id": ["item_1"]}).to_csv(prices_path, index=False)

    bundle = load_m5_dataset(tmp_path)
    assert isinstance(bundle, M5Dataset)
    assert len(bundle.sales_train_validation) == 1
    assert len(bundle.calendar) == 1
    assert len(bundle.sell_prices) == 1

def test_load_m5_dataset_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_m5_dataset(tmp_path)

def test_filter_store_sales():
    df = pd.DataFrame({"store_id": ["CA_1", "CA_2"], "sales": [1, 2]})
    dataset = M5Dataset(calendar=None, sell_prices=None, sales_train_validation=df, weights_validation=None)
    filtered = filter_store_sales(dataset, "CA_1")
    assert len(filtered) == 1
    assert filtered.iloc[0]["store_id"] == "CA_1"
