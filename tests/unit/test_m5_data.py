import pytest
import pandas as pd
from pathlib import Path
from src.models.forecasting.m5_data import M5Dataset, load_m5_dataset, filter_store_sales

def test_load_m5_dataset_no_weights(tmp_path):
    (tmp_path / "calendar.csv").write_text("date\n2020-01-01")
    (tmp_path / "sell_prices.csv").write_text("item,price\nA,1.0")
    (tmp_path / "sales_train_validation.csv").write_text("item,store_id,sales\nA,CA_1,10")
    
    dataset = load_m5_dataset(tmp_path)
    assert len(dataset.calendar) == 1
    assert dataset.weights_validation is None

def test_load_m5_dataset_test_validation_fallback(tmp_path):
    (tmp_path / "calendar.csv").write_text("date\n2020-01-01")
    (tmp_path / "sell_prices.csv").write_text("item,price\nA,1.0")
    # Missing train_validation, fallback to test_validation
    (tmp_path / "sales_test_validation.csv").write_text("item,store_id,sales\nA,CA_1,20")
    (tmp_path / "weights_validation.csv").write_text("Level_id,Agg_Level_1\n1,1")
    
    dataset = load_m5_dataset(tmp_path)
    assert dataset.sales_train_validation.iloc[0]["sales"] == 20
    assert dataset.weights_validation is not None

def test_filter_store_sales():
    cal = pd.DataFrame({"date": ["2020-01-01"]})
    prices = pd.DataFrame({"item": ["A"], "price": [1.0]})
    sales = pd.DataFrame({"store_id": ["CA_1", "CA_2", "CA_1"], "sales": [10, 20, 30]})
    ds = M5Dataset(cal, prices, sales, None)
    
    ca1 = filter_store_sales(ds, "CA_1")
    assert len(ca1) == 2
    assert "CA_2" not in ca1["store_id"].values

def test_filter_store_sales_missing_store_id():
    cal = pd.DataFrame({"date": ["2020-01-01"]})
    prices = pd.DataFrame({"item": ["A"], "price": [1.0]})
    sales = pd.DataFrame({"sales": [10, 20, 30]})
    ds = M5Dataset(cal, prices, sales, None)
    
    with pytest.raises(ValueError, match="must contain store_id"):
        filter_store_sales(ds, "CA_1")
