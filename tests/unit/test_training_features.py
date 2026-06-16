import pandas as pd
from src.models.forecasting.training import engineer_features, build_feature_columns, split_train_validation

def test_engineer_features():
    long_frame = pd.DataFrame({
        "id": ["item1_store1", "item1_store1"],
        "item_id": ["item1", "item1"],
        "dept_id": ["dept1", "dept1"],
        "cat_id": ["cat1", "cat1"],
        "store_id": ["store1", "store1"],
        "state_id": ["state1", "state1"],
        "d_num": [1, 2],
        "d": ["d_1", "d_2"],
        "sales": [10.0, 15.0]
    })
    calendar = pd.DataFrame({
        "d": ["d_1", "d_2"],
        "date": ["2016-01-01", "2016-01-02"],
        "wm_yr_wk": [11601, 11601],
        "weekday": ["Friday", "Saturday"],
        "wday": [1, 2],
        "month": [1, 1],
        "year": [2016, 2016],
        "event_name_1": [None, None],
        "event_type_1": [None, None],
        "event_name_2": [None, None],
        "event_type_2": [None, None],
        "snap_CA": [0, 0],
        "snap_TX": [0, 0],
        "snap_WI": [0, 0]
    })
    prices = pd.DataFrame({
        "store_id": ["store1"],
        "item_id": ["item1"],
        "wm_yr_wk": [11601],
        "sell_price": [1.99]
    })
    
    features = engineer_features(long_frame, calendar, prices)
    assert not features.empty
    assert "sell_price" in features.columns

def test_build_feature_columns():
    df = pd.DataFrame({
        "id": [1], "sales": [1], "d": [1], "date": [1], "d_num": [1],
        "feature1": [1], "feature2": [2]
    })
    cols = build_feature_columns(df)
    assert "feature1" in cols
    assert "feature2" in cols
    assert "id" not in cols

def test_split_train_validation():
    df = pd.DataFrame({
        "d_num": [1, 2, 3, 4, 5],
        "sales": [1, 2, 3, 4, 5]
    })
    train, val = split_train_validation(df, validation_days=2)
    assert len(train) == 3
    assert len(val) == 2
