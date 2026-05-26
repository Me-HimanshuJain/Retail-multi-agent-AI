"""XGBoost forecasting wrapper backed by a trained regressor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

import joblib
import numpy as np
import pandas as pd

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover - optional dependency guard
    XGBRegressor = None


@dataclass
class XGBoostForecaster:
    config: Dict[str, Any] | None = None
    model: Any | None = None
    residual_std: float = 0.0
    is_fitted: bool = False
    feature_names: List[str] = field(default_factory=list)

    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray,
        feature_names: Sequence[str] | None = None,
        params: Dict[str, Any] | None = None,
    ) -> "XGBoostForecaster":
        if XGBRegressor is None:
            raise ImportError("xgboost is required for XGBoostForecaster")

        feature_names = list(feature_names or (list(X.columns) if isinstance(X, pd.DataFrame) else []))
        default_params = {
            "n_estimators": 600,
            "learning_rate": 0.05,
            "max_depth": 8,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "reg_alpha": 0.0,
            "reg_lambda": 1.0,
            "min_child_weight": 1.0,
            "objective": "reg:squarederror",
            "random_state": 42,
            "tree_method": "hist",
            "n_jobs": -1,
        }
        if params:
            default_params.update(params)

        model = XGBRegressor(**default_params)
        model.fit(X, y)
        predictions = model.predict(X)
        self.model = model
        self.residual_std = float(np.std(y - predictions))
        self.is_fitted = True
        self.feature_names = feature_names
        return self

    def predict(self, X: np.ndarray | pd.DataFrame) -> Dict[str, np.ndarray]:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("XGBoostForecaster must be fitted before prediction")

        median = np.asarray(self.model.predict(X), dtype=float)
        spread = max(self.residual_std, 1e-6)
        return {
            "median": median,
            "p10": median - 1.2816 * spread,
            "p90": median + 1.2816 * spread,
        }

    def get_feature_importance(self) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("Model is not available")

        if hasattr(self.model, "feature_importances_") and self.feature_names:
            return pd.DataFrame(
                {
                    "feature": self.feature_names,
                    "importance": self.model.feature_importances_.tolist(),
                }
            )
        return pd.DataFrame(columns=["feature", "importance"])

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Cannot save an unfitted model")
        joblib.dump(
            {
                "model": self.model,
                "residual_std": self.residual_std,
                "feature_names": self.feature_names,
                "config": self.config,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "XGBoostForecaster":
        payload = joblib.load(path)
        model = cls(config=payload.get("config"))
        model.model = payload["model"]
        model.residual_std = float(payload.get("residual_std", 0.0))
        model.feature_names = list(payload.get("feature_names", []))
        model.is_fitted = True
        return model
