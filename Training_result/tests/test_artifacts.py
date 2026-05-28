import os
import sys
import pytest
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / 'src' / 'models' / 'forecasting'
MODEL_DIR = BASE_DIR / 'models'

# Dynamically append the exact training sample source directory to the path
sys.path.append(str(SRC_DIR))

from pipeline import M5Pipeline

def test_model_artifact_loads_and_predicts():
    '''Tests if the LightGBM binary loads and accepts a dynamic dummy payload.'''
    model_path = MODEL_DIR / 'lgb_model_CA_1.bin'
    
    if not model_path.exists():
        pytest.skip(f"Artifact missing at {model_path}, skipping test.")
        
    model = joblib.load(model_path)
    features = model.feature_name()
    assert len(features) > 0, "Model has no features defined."

    dummy_data = pd.DataFrame([np.random.rand(len(features))], columns=features)
    pred = model.predict(dummy_data)

    assert isinstance(pred, np.ndarray), "Prediction should return a numpy array."
    assert len(pred) == 1, "Should return exactly 1 prediction."
    assert not np.isnan(pred[0]), "Prediction resulted in NaN."

def test_pipeline_initialization():
    '''Tests pipeline initialization with required stores list.'''
    pipeline = M5Pipeline(str(MODEL_DIR), ['CA_1'])
    
    assert pipeline.model_dir == str(MODEL_DIR), "Model directory not set correctly."
    assert isinstance(pipeline.models, dict), "Models should be loaded into a dictionary."

def test_pipeline_preprocess_step():
    '''Tests the core lag and rolling window logic of the pipeline.'''
    pipeline = M5Pipeline(str(MODEL_DIR), ['CA_1'])
    
    days = np.arange(1, 31)
    history = pd.DataFrame({
        'id': ['item_1_CA_1_evaluation'] * 30,
        'd_num': days,
        'sales': np.random.randint(1, 10, size=30)
    })
    
    engineered = pipeline.preprocess_step(history.copy())
    
    assert 'lag_7' in engineered.columns, "lag_7 was not generated."
    assert 'lag_28' in engineered.columns, "lag_28 was not generated."
    assert 'rmean_28_7' in engineered.columns, "rmean_28_7 was not generated."
    
    day_30_lag28 = engineered.loc[engineered['d_num'] == 30, 'lag_28'].values[0]
    day_2_sales = history.loc[history['d_num'] == 2, 'sales'].values[0]
    
    assert day_30_lag28 == day_2_sales, "Shift logic failed: lag_28 is incorrect."