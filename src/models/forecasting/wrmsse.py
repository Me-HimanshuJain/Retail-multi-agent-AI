"""Weighted RMSSE evaluation for M5-style forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd


DEFAULT_LEVELS = [
    ("total", ["d_num"]),
    ("state", ["state_id", "d_num"]),
    ("store", ["store_id", "d_num"]),
    ("category", ["cat_id", "d_num"]),
    ("department", ["dept_id", "d_num"]),
    ("state_category", ["state_id", "cat_id", "d_num"]),
    ("state_department", ["state_id", "dept_id", "d_num"]),
    ("store_category", ["store_id", "cat_id", "d_num"]),
    ("store_department", ["store_id", "dept_id", "d_num"]),
    ("item", ["item_id", "d_num"]),
    ("item_state", ["item_id", "state_id", "d_num"]),
    ("item_store", ["id", "d_num"]),
]


@dataclass
class WRMSSEEvaluator:
    train_long: pd.DataFrame
    weights: pd.DataFrame | None = None
    levels: Sequence[tuple[str, List[str]]] = tuple(DEFAULT_LEVELS)

    def __post_init__(self) -> None:
        self._train = self.train_long.copy()
        self._train = self._train.sort_values(["id", "d_num"])
        self._weights_by_level = self._build_level_weights()
        self._scales_by_level = self._build_level_scales()

    def _series_weight_frame(self) -> pd.DataFrame:
        if self.weights is not None and {"id", "weight"}.issubset(self.weights.columns):
            return self.weights[["id", "weight"]].copy()
        frame = self._train.groupby("id", as_index=False)["sales"].sum()
        frame = frame.rename(columns={"sales": "weight"})
        return frame

    def _build_level_weights(self) -> Dict[str, pd.Series]:
        series_weights = self._series_weight_frame()
        merged = self._train[["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]].drop_duplicates()
        merged = merged.merge(series_weights, on="id", how="left").fillna({"weight": 0.0})
        level_weights: Dict[str, pd.Series] = {}
        for level_name, group_cols in self.levels:
            if len(group_cols) == 1:
                level_weights[level_name] = pd.Series({"total": 1.0})
                continue

            grouped = merged.groupby(group_cols[:-1], dropna=False)["weight"].sum()
            total = float(grouped.sum()) or 1.0
            level_weights[level_name] = grouped / total
        return level_weights

    def _scale_for_group(self, values: np.ndarray) -> float:
        non_zero = np.where(values != 0)[0]
        if len(non_zero) == 0:
            return 1.0
        start = int(non_zero[0])
        diffs = np.diff(values[start:])
        if len(diffs) == 0:
            return 1.0
        scale = float(np.mean(np.square(diffs)))
        return scale if scale > 0 else 1.0

    def _build_level_scales(self) -> Dict[str, pd.Series]:
        scales: Dict[str, pd.Series] = {}
        for level_name, group_cols in self.levels:
            group_key = group_cols[:-1]
            if not group_key:
                scales[level_name] = pd.Series({"total": self._scale_for_group(self._train["sales"].to_numpy(dtype=float))})
                continue
            grouped = self._train.groupby(group_key)["sales"].apply(lambda series: self._scale_for_group(series.to_numpy(dtype=float)))
            scales[level_name] = grouped.astype(float)
        return scales

    def _aggregate_frame(self, frame: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
        base_cols = [column for column in group_cols if column != "d_num"]
        aggregated = frame.groupby(base_cols + ["d_num"], as_index=False)["sales"].sum()
        return aggregated

    def score(self, actual_long: pd.DataFrame, predicted_long: pd.DataFrame) -> float:
        actual = actual_long.copy()
        predicted = predicted_long.copy()
        total_scores: List[float] = []

        for level_name, group_cols in self.levels:
            actual_agg = self._aggregate_frame(actual, group_cols)
            predicted_agg = self._aggregate_frame(predicted, group_cols)
            group_key = group_cols[:-1]
            level_scales = self._scales_by_level[level_name]
            level_weights = self._weights_by_level[level_name]
            merged = actual_agg.merge(predicted_agg, on=[column for column in group_cols], suffixes=("_actual", "_pred"))

            if not group_key:
                actual_values = merged["sales_actual"].to_numpy(dtype=float)
                predicted_values = merged["sales_pred"].to_numpy(dtype=float)
                scale = float(level_scales.get("total", 1.0))
                total_scores.append(float(np.sqrt(np.mean((actual_values - predicted_values) ** 2) / scale)))
                continue

            grouped = merged.groupby(group_key, dropna=False)
            level_score = 0.0
            total_weight = 0.0
            for key, chunk in grouped:
                key_tuple = key if isinstance(key, tuple) else (key,)
                series_key = key_tuple if len(key_tuple) > 1 else key_tuple[0]
                actual_values = chunk["sales_actual"].to_numpy(dtype=float)
                predicted_values = chunk["sales_pred"].to_numpy(dtype=float)
                scale = float(level_scales.get(series_key, 1.0))
                weight = float(level_weights.get(series_key, 0.0))
                rmsse = float(np.sqrt(np.mean((actual_values - predicted_values) ** 2) / scale))
                level_score += weight * rmsse
                total_weight += weight
            if total_weight > 0:
                total_scores.append(level_score / total_weight)

        return float(np.mean(total_scores)) if total_scores else 0.0
