import numpy as np
import pandas as pd
import joblib
import os
import gc

# ---------------------------------------------------------
# CRITICAL FIX 1: Import exact training feature logic
# (Assumes you saved your training functions to a file named 'features.py')
# ---------------------------------------------------------
from features import create_features, reduce_mem_usage

class M5Pipeline:
    def __init__(self, model_dir, stores):
        self.model_dir = model_dir
        self.stores = stores
        
        # Pre-load all models into memory ONCE
        self.models = self._load_models()

    def _load_models(self):
        print("Loading models into memory...")
        models = {}
        for store in self.stores:
            model_path = os.path.join(self.model_dir, f'lgb_model_{store}.bin')
            if os.path.exists(model_path):
                models[store] = joblib.load(model_path)
            else:
                print(f"Warning: Model for {store} not found!")
        return models

    def preprocess_step(self, df):
        '''
        Calculates dynamic rolling lags. Assumes dataframe is sorted chronologically.
        '''
        df['lag_7'] = df.groupby('id')['sales'].shift(7).astype(np.float32)
        df['lag_14'] = df.groupby('id')['sales'].shift(14).astype(np.float32)
        df['lag_28'] = df.groupby('id')['sales'].shift(28).astype(np.float32)

        for w in [7, 14, 28]:
            df[f'rmean_28_{w}'] = df.groupby('id')['lag_28'].transform(lambda x: x.rolling(w).mean()).astype(np.float32)
            df[f'rstd_28_{w}'] = df.groupby('id')['lag_28'].transform(lambda x: x.rolling(w).std()).astype(np.float32)
            
        return df

    def predict_one_step(self, history_df, static_features_df, target_d_num):
        '''
        Predicts exactly 1 step ahead for a specific day.
        '''
        # 1. Generate Lags based on current history
        engineered = self.preprocess_step(history_df)

        # 2. Extract the target day
        target = engineered[engineered['d_num'] == target_d_num].copy()
        if 'sales' in target.columns:
            target = target.drop(columns=['sales'])

        # 3. Merge with calendar/prices (static features)
        target = target.merge(static_features_df, on=['id', 'd_num'], how='left')

        predictions = []

        # 4. Predict per store
        for store, model in self.models.items():
            
            # CRITICAL FIX 2: Safe Exact Match before categorical encoding
            store_mask = (target['store_id'] == store)
            if not store_mask.any():
                continue
                
            store_data = target[store_mask].copy()
            
            # Now apply the exact training feature engineering to this batch
            store_data = create_features(reduce_mem_usage(store_data))
            
            # Safely intersect required features to prevent LightGBM crashes
            required_features = [f for f in model.feature_name() if f in store_data.columns]
            X = store_data[required_features]
            
            preds = model.predict(X)
            
            res = store_data[['id']].copy()
            res['sales'] = preds
            predictions.append(res)
            
        return pd.concat(predictions)

    def recursive_forecast(self, history_df, static_features_df, future_d_nums):
        '''
        Executes the recursive day-by-day forecasting loop.
        '''
        print(f"Starting recursive forecast for {len(future_d_nums)} days...")
        current_history = history_df.copy()
        
        for d_num in future_d_nums:
            # Predict the specific day
            day_preds = self.predict_one_step(current_history, static_features_df, d_num)
            
            mask = (current_history['d_num'] == d_num)
            pred_map = day_preds.set_index('id')['sales']
            
            # CRITICAL FIX 3: Safe map with fillna to prevent wiping data
            current_history.loc[mask, 'sales'] = (
                current_history.loc[mask, 'id']
                .map(pred_map)
                .fillna(current_history.loc[mask, 'sales'])
            )
            
            print(f"Day {d_num} predicted.")
            
        # Return only the future predictions
        return current_history[current_history['d_num'].isin(future_d_nums)][['id', 'd_num', 'sales']]