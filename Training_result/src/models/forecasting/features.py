import pandas as pd
import numpy as np


def reduce_mem_usage(df):
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    for col in df.columns:
        col_type = df[col].dtypes
        if col_type in numerics:
            c_min, c_max = df[col].min(), df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float16)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
    return df


def create_features(df):
    df['date'] = pd.to_datetime(df['date'])
    df['wday'] = df['date'].dt.dayofweek.astype(np.int8)
    df['mday'] = df['date'].dt.day.astype(np.int8)
    df['week'] = df['date'].dt.isocalendar().week.astype(np.int8)
    df['month'] = df['date'].dt.month.astype(np.int8)

    df['price_max'] = df.groupby(['store_id', 'item_id'])['sell_price'].transform('max')
    df['price_min'] = df.groupby(['store_id', 'item_id'])['sell_price'].transform('min')
    df['price_std'] = df.groupby(['store_id', 'item_id'])['sell_price'].transform('std')
    df['price_momentum'] = df['sell_price'] / df.groupby(['store_id', 'item_id'])['sell_price'].shift(1)

    lags = [7, 14, 28]
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby('id')['sales'].shift(lag).astype(np.float16)

    for window in [7, 14, 28]:
        df[f'rmean_28_{window}'] = df.groupby('id')['lag_28'].transform(lambda x: x.rolling(window).mean()).astype(np.float16)
        df[f'rstd_28_{window}'] = df.groupby('id')['lag_28'].transform(lambda x: x.rolling(window).std()).astype(np.float16)

    cat_cols = ['item_id', 'dept_id', 'cat_id', 'store_id', 'state_id', 'event_name_1', 'event_type_1', 'event_name_2', 'event_type_2', 'weekday']
    for col in cat_cols:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].astype('category').cat.codes.astype(np.int16)

    return df