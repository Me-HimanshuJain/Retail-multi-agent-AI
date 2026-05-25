"""Simple forecasting model wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class ProphetForecaster:
    config: Dict | None = None
    history: pd.DataFrame | None = None
    is_fitted: bool = False
    baseline: float = 0.0

    def fit(self, df: pd.DataFrame) -> "ProphetForecaster":
        self.history = df.copy()
        self.baseline = float(df["y"].mean())
        self.is_fitted = True
        return self

    def predict(self, periods: int = 7) -> pd.DataFrame:
        values = np.full(periods, self.baseline)
        return pd.DataFrame({"ds": pd.date_range(self.history["ds"].max(), periods=periods + 1, freq="D")[1:], "yhat": values})

    def predict_quantiles(self, periods: int = 7) -> Dict[str, List[float]]:
        center = [self.baseline for _ in range(periods)]
        return {"median": center, "p10": [v * 0.9 for v in center], "p90": [v * 1.1 for v in center]}

    def save(self, path: str) -> None:
        pd.Series({"baseline": self.baseline, "is_fitted": self.is_fitted}).to_json(path)

    @classmethod
    def load(cls, path: str) -> "ProphetForecaster":
        data = pd.read_json(path, typ="series")
        model = cls()
        model.baseline = float(data["baseline"])
        model.is_fitted = bool(data["is_fitted"])
        return model
