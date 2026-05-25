"""Simple tabular forecasting wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class XGBoostForecaster:
    config: Dict | None = None
    is_fitted: bool = False
    feature_names: List[str] = field(default_factory=list)
    baseline: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: List[str] | None = None) -> "XGBoostForecaster":
        self.baseline = float(np.mean(y))
        self.is_fitted = True
        self.feature_names = feature_names or []
        return self

    def predict(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        median = np.full(len(X), self.baseline)
        return {"median": median, "p10": median * 0.9, "p90": median * 1.1}

    def get_feature_importance(self) -> pd.DataFrame:
        return pd.DataFrame({"feature": self.feature_names, "importance": np.linspace(1.0, 0.1, num=len(self.feature_names))})

    def save(self, path: str) -> None:
        pd.Series({"baseline": self.baseline, "is_fitted": self.is_fitted, "feature_names": self.feature_names}).to_json(path)

    @classmethod
    def load(cls, path: str) -> "XGBoostForecaster":
        data = pd.read_json(path, typ="series")
        model = cls()
        model.baseline = float(data["baseline"])
        model.is_fitted = bool(data["is_fitted"])
        model.feature_names = list(data.get("feature_names", []))
        return model
