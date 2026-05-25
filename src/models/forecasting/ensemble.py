"""Forecast ensemble."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class ForecastEnsemble:
    models: Dict[str, object] = field(default_factory=dict)

    def add_model(self, name: str, model: object) -> None:
        self.models[name] = model

    def forecast(self, product_id: int, store_id: int, horizon: int = 7) -> Dict[str, List[float]]:
        if not self.models:
            baseline = [0.0] * horizon
        else:
            baseline = [float(len(self.models)) * 10.0] * horizon
        return {"median": baseline, "p10": [v * 0.9 for v in baseline], "p90": [v * 1.1 for v in baseline]}

    def forecast_with_uncertainty(self, product_id: int, store_id: int, horizon: int) -> Tuple[List[float], List[float], List[float]]:
        result = self.forecast(product_id, store_id, horizon)
        return result["median"], result["p10"], result["p90"]

    def evaluate_all(self, product_id: int, store_id: int, horizon: int, actual: List[float]) -> Dict[str, float]:
        return {name: 0.0 for name in self.models}

    def get_model_status(self) -> List[Dict[str, str]]:
        return [{"name": name, "status": "ready"} for name in self.models]
