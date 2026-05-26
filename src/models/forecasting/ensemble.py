"""Weighted forecast ensemble over learned model outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class ForecastEnsemble:
    models: Dict[str, object] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)

    def add_model(self, name: str, model: object) -> None:
        self.models[name] = model

    def fit_weights(self, validation_predictions: pd.DataFrame, actual_col: str = "actual") -> Dict[str, float]:
        model_columns = [column for column in validation_predictions.columns if column != actual_col]
        if not model_columns:
            raise ValueError("validation_predictions must contain at least one model column")

        matrix = validation_predictions[model_columns].to_numpy(dtype=float)
        actual = validation_predictions[actual_col].to_numpy(dtype=float)

        def objective(weight_vector: np.ndarray) -> float:
            blended = matrix @ weight_vector
            return float(np.mean((actual - blended) ** 2))

        constraints = ({"type": "eq", "fun": lambda weight_vector: np.sum(weight_vector) - 1.0},)
        bounds = [(0.0, 1.0) for _ in model_columns]
        start = np.full(len(model_columns), 1.0 / len(model_columns))
        result = minimize(objective, start, bounds=bounds, constraints=constraints)
        if not result.success:
            raise RuntimeError(f"Failed to optimize ensemble weights: {result.message}")

        self.weights = {name: float(weight) for name, weight in zip(model_columns, result.x)}
        return self.weights

    def combine(self, member_forecasts: Mapping[str, np.ndarray]) -> Dict[str, np.ndarray]:
        if not member_forecasts:
            raise ValueError("member_forecasts cannot be empty")

        member_names = list(member_forecasts)
        aligned = [np.asarray(member_forecasts[name], dtype=float) for name in member_names]
        lengths = {array.shape[0] for array in aligned}
        if len(lengths) != 1:
            raise ValueError("All member forecasts must have the same horizon")

        horizon = aligned[0].shape[0]
        if not self.weights:
            weight_vector = np.full(len(member_names), 1.0 / len(member_names))
        else:
            weight_vector = np.asarray([self.weights.get(name, 0.0) for name in member_names], dtype=float)
            if weight_vector.sum() == 0:
                weight_vector = np.full(len(member_names), 1.0 / len(member_names))
            else:
                weight_vector = weight_vector / weight_vector.sum()

        forecast_matrix = np.vstack(aligned)
        median = weight_vector @ forecast_matrix
        spread = np.std(forecast_matrix, axis=0)
        return {"median": median, "p10": median - 1.2816 * spread, "p90": median + 1.2816 * spread}

    def forecast(self, member_forecasts: Mapping[str, np.ndarray]) -> Dict[str, np.ndarray]:
        return self.combine(member_forecasts)

    def forecast_with_uncertainty(self, member_forecasts: Mapping[str, np.ndarray]) -> tuple[List[float], List[float], List[float]]:
        result = self.combine(member_forecasts)
        return result["median"].tolist(), result["p10"].tolist(), result["p90"].tolist()

    def evaluate_all(self, validation_predictions: pd.DataFrame, actual_col: str = "actual") -> Dict[str, float]:
        if actual_col not in validation_predictions.columns:
            raise ValueError("actual column missing")
        metrics: Dict[str, float] = {}
        actual = validation_predictions[actual_col].to_numpy(dtype=float)
        for name in validation_predictions.columns:
            if name == actual_col:
                continue
            predicted = validation_predictions[name].to_numpy(dtype=float)
            metrics[name] = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        return metrics

    def get_model_status(self) -> List[Dict[str, str]]:
        return [{"name": name, "status": "trained"} for name in self.models]

    def save(self, path: str | Path) -> None:
        joblib.dump({"models": self.models, "weights": self.weights}, path)

    @classmethod
    def load(cls, path: str | Path) -> "ForecastEnsemble":
        payload = joblib.load(path)
        return cls(models=payload.get("models", {}), weights=payload.get("weights", {}))
