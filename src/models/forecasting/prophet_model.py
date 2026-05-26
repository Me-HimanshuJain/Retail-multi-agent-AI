"""Prophet-style forecasting wrapper backed by a real seasonal model.

The wrapper uses Prophet when the backend is available. On Windows systems
without a working CmdStan toolchain, it falls back to a real seasonal
statsmodels forecaster so the repository still trains and predicts without
fake outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

try:
    from prophet import Prophet
except Exception:  # pragma: no cover - optional dependency guard
    Prophet = None


@dataclass
class ProphetForecaster:
    config: Dict[str, Any] | None = None
    history: pd.DataFrame | None = None
    model: Any | None = None
    residual_std: float = 0.0
    is_fitted: bool = False
    regressors: List[str] = field(default_factory=list)
    backend: str = "prophet"

    def fit(self, df: pd.DataFrame, regressors: Sequence[str] | None = None) -> "ProphetForecaster":
        frame = df.copy()
        frame["ds"] = pd.to_datetime(frame["ds"])
        frame = frame.sort_values("ds")
        self.history = frame[["ds", "y"] + list(regressors or [])].copy()
        self.regressors = list(regressors or [])

        prophet_allowed = Prophet is not None
        if prophet_allowed:
            try:
                model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=False,
                    interval_width=0.8,
                    **(self.config or {}),
                )
                for regressor in self.regressors:
                    model.add_regressor(regressor)
                model.fit(self.history)
                in_sample = model.predict(self.history)
                self.residual_std = float(np.std(self.history["y"].to_numpy() - in_sample["yhat"].to_numpy()))
                self.model = model
                self.backend = "prophet"
                self.is_fitted = True
                return self
            except Exception:
                prophet_allowed = False

        values = frame["y"].to_numpy(dtype=float)
        seasonal_periods = int(self.config.get("seasonal_periods", 7)) if self.config else 7
        if len(values) >= max(2 * seasonal_periods, 10):
            model = ExponentialSmoothing(
                values,
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_periods,
            ).fit(optimized=True)
        else:
            model = ExponentialSmoothing(values, trend="add", seasonal=None).fit(optimized=True)

        fitted = np.asarray(model.fittedvalues, dtype=float)
        self.residual_std = float(np.std(values - fitted))
        self.model = model
        self.backend = "holtwinters"
        self.is_fitted = True
        return self

    def predict(self, periods: int = 7, future_df: pd.DataFrame | None = None) -> pd.DataFrame:
        if not self.is_fitted or self.model is None or self.history is None:
            raise RuntimeError("ProphetForecaster must be fitted before prediction")

        if self.backend == "prophet":
            if future_df is not None:
                future = future_df.copy()
                future["ds"] = pd.to_datetime(future["ds"])
            else:
                future = self.model.make_future_dataframe(periods=periods, freq="D", include_history=False)
                for regressor in self.regressors:
                    future[regressor] = np.nan

            forecast = self.model.predict(future)
            return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

        horizon_index = pd.date_range(self.history["ds"].max(), periods=periods + 1, freq="D")[1:]
        forecast_values = np.asarray(self.model.forecast(periods), dtype=float)
        spread = max(self.residual_std, 1e-6)
        return pd.DataFrame(
            {
                "ds": horizon_index,
                "yhat": forecast_values,
                "yhat_lower": forecast_values - 1.2816 * spread,
                "yhat_upper": forecast_values + 1.2816 * spread,
            }
        )

    def predict_quantiles(self, periods: int = 7, future_df: pd.DataFrame | None = None) -> Dict[str, List[float]]:
        forecast = self.predict(periods=periods, future_df=future_df)
        return {
            "median": forecast["yhat"].astype(float).tolist(),
            "p10": forecast["yhat_lower"].astype(float).tolist(),
            "p90": forecast["yhat_upper"].astype(float).tolist(),
        }

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Cannot save an unfitted model")
        joblib.dump(
            {
                "model": self.model,
                "history": self.history,
                "residual_std": self.residual_std,
                "is_fitted": self.is_fitted,
                "regressors": self.regressors,
                "config": self.config,
                "backend": self.backend,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "ProphetForecaster":
        payload = joblib.load(path)
        model = cls(config=payload.get("config"))
        model.model = payload["model"]
        model.history = payload.get("history")
        model.residual_std = float(payload.get("residual_std", 0.0))
        model.is_fitted = bool(payload.get("is_fitted", False))
        model.regressors = list(payload.get("regressors", []))
        model.backend = str(payload.get("backend", "prophet"))
        return model
