import pandas as pd
import numpy as np
from src.models.forecasting.wrmsse import WRMSSEEvaluator

def test_wrmsse_evaluator_score():
    train_long = pd.DataFrame({
        "id": ["item1_store1", "item1_store1"],
        "item_id": ["item1", "item1"],
        "dept_id": ["dept1", "dept1"],
        "cat_id": ["cat1", "cat1"],
        "store_id": ["store1", "store1"],
        "state_id": ["state1", "state1"],
        "d_num": [1, 2],
        "sales": [10.0, 15.0]
    })
    
    evaluator = WRMSSEEvaluator(train_long)
    
    actual = pd.DataFrame({
        "id": ["item1_store1"],
        "item_id": ["item1"],
        "dept_id": ["dept1"],
        "cat_id": ["cat1"],
        "store_id": ["store1"],
        "state_id": ["state1"],
        "d_num": [3],
        "sales": [20.0]
    })
    
    predicted = pd.DataFrame({
        "id": ["item1_store1"],
        "item_id": ["item1"],
        "dept_id": ["dept1"],
        "cat_id": ["cat1"],
        "store_id": ["store1"],
        "state_id": ["state1"],
        "d_num": [3],
        "sales": [18.0]
    })
    
    score = evaluator.score(actual, predicted)
    assert score >= 0
