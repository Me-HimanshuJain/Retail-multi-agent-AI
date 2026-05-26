"""Forecast training helpers and real M5-style feature pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import TimeSeriesSplit

from .evaluation import evaluate_forecast
from .prophet_model import ProphetForecaster
from .xgboost_model import XGBoostForecaster
from .wrmsse import WRMSSEEvaluator

try:
    import optuna
except Exception:  # pragma: no cover - optional dependency guard
    optuna = None


ID_COLUMNS = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
LAG_FEATURES = [7, 14, 28]
ROLL_WINDOWS = [7, 14, 28]


@dataclass
class M5Bundle:
    sales: pd.DataFrame
    calendar: pd.DataFrame
    prices: pd.DataFrame
    weights: pd.DataFrame | None = None


def load_m5_bundle(data_dir: str | Path) -> M5Bundle:
    base = Path(data_dir)
    sales = pd.read_csv(base / "sales_train_evaluation.csv")
    calendar = pd.read_csv(base / "calendar.csv")
    prices = pd.read_csv(base / "sell_prices.csv")
    weights_path = base / "weights.csv"
    weights = pd.read_csv(weights_path) if weights_path.exists() else None
    return M5Bundle(sales=sales, calendar=calendar, prices=prices, weights=weights)


def _ensure_identifier_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if "id" not in frame.columns and {"item_id", "store_id"}.issubset(frame.columns):
        frame["id"] = frame["item_id"].astype(str).str.strip() + "_" + frame["store_id"].astype(str).str.strip() + "_evaluation"
    return frame


def melt_sales_frame(sales_df: pd.DataFrame) -> pd.DataFrame:
    frame = _ensure_identifier_columns(sales_df)
    day_columns = [column for column in frame.columns if column.startswith("d_")]
    long_frame = frame.melt(id_vars=ID_COLUMNS, value_vars=day_columns, var_name="d", value_name="sales")
    long_frame["d_num"] = long_frame["d"].str.replace("d_", "", regex=False).astype(int)
    return long_frame


def _encode_categoricals(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    encoded = frame.copy()
    for column in columns:
        if column in encoded.columns and encoded[column].dtype == "object":
            encoded[column] = encoded[column].astype("category").cat.codes.astype(np.int32)
    return encoded


def engineer_features(long_frame: pd.DataFrame, calendar_df: pd.DataFrame, prices_df: pd.DataFrame) -> pd.DataFrame:
    frame = long_frame.copy()
    calendar = calendar_df.copy()
    calendar.columns = calendar.columns.str.strip()
    prices = prices_df.copy()
    prices.columns = prices.columns.str.strip()

    if "d" not in calendar.columns:
        calendar = calendar.reset_index(drop=True)
        calendar["d"] = [f"d_{index + 1}" for index in range(len(calendar))]

    if "date" not in calendar.columns and "d" in calendar.columns:
        calendar["date"] = pd.to_datetime(calendar["wm_yr_wk"], errors="coerce")
    elif "date" in calendar.columns:
        calendar["date"] = pd.to_datetime(calendar["date"])

    frame = frame.merge(calendar, on="d", how="left")
    price_key = [column for column in ["store_id", "item_id", "wm_yr_wk"] if column in prices.columns]
    if len(price_key) == 3:
        frame = frame.merge(prices, on=price_key, how="left")

    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
        frame["dayofweek"] = frame["date"].dt.dayofweek.astype(np.int16)
        frame["day"] = frame["date"].dt.day.astype(np.int16)
        frame["week"] = frame["date"].dt.isocalendar().week.astype(np.int16)
        frame["month"] = frame["date"].dt.month.astype(np.int16)
        frame["quarter"] = frame["date"].dt.quarter.astype(np.int16)

    if "sell_price" in frame.columns:
        group = frame.groupby(["store_id", "item_id"])["sell_price"]
        frame["sell_price_max"] = group.transform("max")
        frame["sell_price_min"] = group.transform("min")
        frame["sell_price_std"] = group.transform("std")
        frame["sell_price_momentum"] = group.transform(lambda series: series / series.shift(1))

    frame = frame.sort_values(["id", "d_num"]).reset_index(drop=True)
    for lag in LAG_FEATURES:
        frame[f"lag_{lag}"] = frame.groupby("id")["sales"].shift(lag)

    lag_base = frame.groupby("id")["sales"].shift(28)
    for window in ROLL_WINDOWS:
        frame[f"rmean_28_{window}"] = lag_base.groupby(frame["id"]).transform(lambda series: series.rolling(window).mean())
        frame[f"rstd_28_{window}"] = lag_base.groupby(frame["id"]).transform(lambda series: series.rolling(window).std())

    categorical_columns = [
        "item_id",
        "dept_id",
        "cat_id",
        "store_id",
        "state_id",
        "event_name_1",
        "event_type_1",
        "event_name_2",
        "event_type_2",
        "weekday",
    ]
    frame = _encode_categoricals(frame, categorical_columns)
    return frame


def build_feature_columns(frame: pd.DataFrame) -> List[str]:
    excluded = {"id", "sales", "d", "date", "d_num"}
    return [column for column in frame.columns if column not in excluded]


def split_train_validation(frame: pd.DataFrame, validation_days: int = 28) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_days = sorted(int(day) for day in frame["d_num"].dropna().unique())
    if len(unique_days) < 2:
        raise ValueError("Need at least two unique days to split train and validation")

    effective_validation_days = min(max(validation_days, 1), len(unique_days) - 1)
    cutoff_idx = len(unique_days) - effective_validation_days - 1
    cutoff = unique_days[cutoff_idx]

    train = frame[frame["d_num"] <= cutoff].copy()
    validation = frame[frame["d_num"] > cutoff].copy()

    if train.empty or validation.empty:
        midpoint = len(unique_days) // 2
        cutoff = unique_days[midpoint - 1]
        train = frame[frame["d_num"] <= cutoff].copy()
        validation = frame[frame["d_num"] > cutoff].copy()

    return train, validation


def prepare_prophet_data(df: pd.DataFrame, product_id: int | str | None = None, store_id: int | str | None = None) -> pd.DataFrame:
    frame = df.copy()
    frame["ds"] = pd.to_datetime(frame["ds"])
    if product_id is not None and "product_id" in frame.columns:
        frame = frame[frame["product_id"] == product_id]
    if store_id is not None and "store_id" in frame.columns:
        frame = frame[frame["store_id"] == store_id]
    return frame[["ds", "y"] + [column for column in frame.columns if column not in {"ds", "y"}]].sort_values("ds")


def prepare_xgboost_data(df: pd.DataFrame, product_id: int | str | None = None, store_id: int | str | None = None, lookback: int = 28) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    frame = df.copy()
    if product_id is not None and "product_id" in frame.columns:
        frame = frame[frame["product_id"] == product_id]
    if store_id is not None and "store_id" in frame.columns:
        frame = frame[frame["store_id"] == store_id]
    values = frame.sort_values("ds")["y"].to_numpy(dtype=float)
    if len(values) <= lookback:
        return np.empty((0, lookback)), np.empty((0,)), [f"lag_{index}" for index in range(lookback)]
    x_rows: List[List[float]] = []
    y_values: List[float] = []
    for index in range(lookback, len(values)):
        x_rows.append(values[index - lookback:index].tolist())
        y_values.append(float(values[index]))
    feature_cols = [f"lag_{index}" for index in range(lookback)]
    return np.asarray(x_rows, dtype=float), np.asarray(y_values, dtype=float), feature_cols


def compute_metric_bundle(actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
    return evaluate_forecast(np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float))


def _optuna_lgbm_params(train_x: pd.DataFrame, train_y: pd.Series, validation_x: pd.DataFrame, validation_y: pd.Series, n_trials: int) -> Dict[str, float | int]:
    if optuna is None or n_trials <= 0:
        return {
            "n_estimators": 800,
            "learning_rate": 0.05,
            "num_leaves": 128,
            "min_child_samples": 25,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "reg_alpha": 0.0,
            "reg_lambda": 1.0,
        }

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": 1200,
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 31, 256),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 120),
            "subsample": trial.suggest_float("subsample", 0.7, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 2.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 5.0),
        }
        model = LGBMRegressor(
            objective="regression",
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
            **params,
        )
        time_split = TimeSeriesSplit(n_splits=3)
        fold_scores: List[float] = []
        for train_index, valid_index in time_split.split(train_x):
            fold_train_x = train_x.iloc[train_index]
            fold_train_y = train_y.iloc[train_index]
            fold_valid_x = train_x.iloc[valid_index]
            fold_valid_y = train_y.iloc[valid_index]
            model.fit(fold_train_x, fold_train_y, eval_set=[(fold_valid_x, fold_valid_y)])
            prediction = model.predict(fold_valid_x)
            fold_scores.append(float(np.sqrt(np.mean((fold_valid_y.to_numpy() - prediction) ** 2))))
        if fold_scores:
            return float(np.mean(fold_scores))

        model.fit(train_x, train_y, eval_set=[(validation_x, validation_y)])
        prediction = model.predict(validation_x)
        return float(np.sqrt(np.mean((validation_y.to_numpy() - prediction) ** 2)))

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)
    best = dict(study.best_params)
    best["n_estimators"] = 1200
    return best


def train_lightgbm_model(train_frame: pd.DataFrame, validation_frame: pd.DataFrame, feature_columns: Sequence[str], target_column: str = "sales", n_trials: int = 0) -> tuple[LGBMRegressor, Dict[str, float]]:
    train_x = train_frame[list(feature_columns)]
    train_y = train_frame[target_column]
    validation_x = validation_frame[list(feature_columns)]
    validation_y = validation_frame[target_column]
    params = _optuna_lgbm_params(train_x, train_y, validation_x, validation_y, n_trials)
    model = LGBMRegressor(objective="regression", random_state=42, n_jobs=-1, verbosity=-1, **params)
    model.fit(train_x, train_y, eval_set=[(validation_x, validation_y)])
    prediction = model.predict(validation_x)
    metrics = compute_metric_bundle(validation_y.to_numpy(), prediction)
    return model, metrics


def train_xgboost_model(train_frame: pd.DataFrame, validation_frame: pd.DataFrame, feature_columns: Sequence[str], target_column: str = "sales") -> tuple[XGBoostForecaster, Dict[str, float]]:
    model = XGBoostForecaster()
    model.fit(train_frame[list(feature_columns)], train_frame[target_column].to_numpy(), feature_names=feature_columns)
    validation_prediction = model.predict(validation_frame[list(feature_columns)])
    metrics = compute_metric_bundle(validation_frame[target_column].to_numpy(), validation_prediction["median"])
    return model, metrics


def train_prophet_model(series_frame: pd.DataFrame) -> ProphetForecaster:
    prophet_frame = series_frame[["ds", "y"] + [column for column in series_frame.columns if column not in {"ds", "y"}]].copy()
    model = ProphetForecaster()
    model.fit(prophet_frame)
    return model


def build_wrmsse_evaluator(train_long: pd.DataFrame, weights: pd.DataFrame | None = None) -> WRMSSEEvaluator:
    return WRMSSEEvaluator(train_long=train_long, weights=weights)


def train_forecasting_workflow(data_dir: str | Path, model_dir: str | Path, validation_days: int = 28, n_trials: int = 0) -> Dict[str, Dict[str, float]]:
    bundle = load_m5_bundle(data_dir)
    long_frame = melt_sales_frame(bundle.sales)
    feature_frame = engineer_features(long_frame, bundle.calendar, bundle.prices)
    feature_frame = feature_frame.dropna(subset=["sales"])
    feature_columns = build_feature_columns(feature_frame)
    train_frame, validation_frame = split_train_validation(feature_frame, validation_days=validation_days)

    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    lgbm_model, lgbm_metrics = train_lightgbm_model(train_frame, validation_frame, feature_columns, n_trials=n_trials)
    lgbm_model.booster_.save_model(str(model_path / "m5_lgbm.bin"))

    xgb_model, xgb_metrics = train_xgboost_model(train_frame, validation_frame, feature_columns)
    xgb_model.save(model_path / "m5_xgb.bin")

    prophet_series = prepare_prophet_data(
        pd.DataFrame(
            {
                "ds": pd.to_datetime(feature_frame["date"]),
                "y": feature_frame["sales"],
                "product_id": feature_frame["item_id"],
                "store_id": feature_frame["store_id"],
            }
        )
    )
    prophet_model = train_prophet_model(prophet_series)
    prophet_model.save(model_path / "m5_prophet.bin")

    weights = bundle.weights
    wrmsse = build_wrmsse_evaluator(long_frame, weights)
    validation_predictions = validation_frame[["id", "d_num", "sales"]].copy()
    validation_predictions["lgbm"] = lgbm_model.predict(validation_frame[feature_columns])
    validation_predictions["xgb"] = xgb_model.predict(validation_frame[feature_columns])["median"]
    actual_long = validation_frame[["id", "d_num", "sales"]].copy()
    wrmsse_score = wrmsse.score(actual_long=actual_long, predicted_long=validation_predictions[["id", "d_num", "lgbm"]].rename(columns={"lgbm": "sales"}))

    return {
        "lgbm": {**lgbm_metrics, "wrmsse": wrmsse_score},
        "xgb": xgb_metrics,
    }
