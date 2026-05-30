"""Demand generator — bridges trained LightGBM model artifacts to the simulation loop.

Key design decisions
--------------------
- Builds the exact 35 M5 features the trained models were trained on.
- Falls back to a realistic statistical baseline (Poisson + seasonality) if
  no artifact is found, so the simulation still runs without trained models.
- Applies ExternalFactors.demand_multiplier so holidays/weekends affect demand.
- Rolling history: appends each generated value so tomorrow's lag features
  are computed from real simulation history, not constants.
- Exposes get_demand(day) and get_forecast_range(day, days) used by
  SmartInventoryAgent and the simulation loop.
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from src.simulation.external_factors import ExternalFactorsGenerator
from src.models.forecasting.ensemble import ForecastEnsemble

# ---------------------------------------------------------------------------
# Model directory
# ---------------------------------------------------------------------------
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))

# Last M5 training day = d_1941 = 2016-05-22
_M5_BASE_DATE = datetime(2016, 5, 22)

# Smoothing: blend raw model output with recent history to prevent lag collapse
_SMOOTH_ALPHA = 0.35

# Store metadata — label-encoded exactly as notebook's create_features()
_STORE_META: dict[str, dict] = {
    "CA_1": {"store_id": 0, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 2.98},
    "CA_2": {"store_id": 1, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 3.12},
    "CA_3": {"store_id": 2, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 2.75},
    "CA_4": {"store_id": 3, "state_id": 0, "snap_CA": 1, "snap_TX": 0, "snap_WI": 0, "sell_price": 3.49},
    "TX_1": {"store_id": 4, "state_id": 1, "snap_CA": 0, "snap_TX": 1, "snap_WI": 0, "sell_price": 2.50},
    "TX_2": {"store_id": 5, "state_id": 1, "snap_CA": 0, "snap_TX": 1, "snap_WI": 0, "sell_price": 2.89},
    "TX_3": {"store_id": 6, "state_id": 1, "snap_CA": 0, "snap_TX": 1, "snap_WI": 0, "sell_price": 3.25},
    "WI_1": {"store_id": 7, "state_id": 2, "snap_CA": 0, "snap_TX": 0, "snap_WI": 1, "sell_price": 2.65},
    "WI_2": {"store_id": 8, "state_id": 2, "snap_CA": 0, "snap_TX": 0, "snap_WI": 1, "sell_price": 2.79},
    "WI_3": {"store_id": 9, "state_id": 2, "snap_CA": 0, "snap_TX": 0, "snap_WI": 1, "sell_price": 3.10},
}


# ---------------------------------------------------------------------------
# Statistical fallback (used when no model artifact is found)
# ---------------------------------------------------------------------------

class _StatisticalBaseline:
    """Realistic fallback: Poisson demand with trend + weekly + annual seasonality."""

    def __init__(self, store_id: str, base_demand: float = 10.0, seed: int = 42):
        store_hash = hash(store_id) % (2 ** 31)
        self.rng  = np.random.default_rng(seed ^ store_hash)
        self.base = base_demand

    def predict(self, day_index: int, date: datetime) -> float:
        trend    = 1.0 + 0.001 * day_index
        weekend  = 1.15 if date.weekday() >= 5 else 1.0
        seasonal = 1.20 if date.month in (11, 12, 1) else (0.90 if date.month in (6, 7) else 1.0)
        mu       = self.base * trend * weekend * seasonal
        return float(self.rng.poisson(max(1.0, mu)))


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class DemandGenerator:
    """Load a trained LightGBM artifact and produce per-day demand for one store.

    Falls back to _StatisticalBaseline if the model file is missing.

    Parameters
    ----------
    store_id    : Store name matching model filename, e.g. "CA_1".
    model_type  : "lgbm" (default) — XGBoost not used here (LightGBM has real artifacts).
    external_factors : Shared ExternalFactorsGenerator from the simulator.
    seed        : Random seed for fallback baseline noise.
    base_demand : Baseline demand units/day used by the fallback.
    """

    def __init__(
        self,
        store_id: str,
        model_type: str = "lgbm",
        external_factors: Optional[ExternalFactorsGenerator] = None,
        seed: int = 42,
        base_demand: float = 10.0,
        # legacy args accepted but ignored
        model_dir: str | Path = "models",
        start_date: Optional[datetime] = None,
        initial_lag: float = 10.0,
    ) -> None:
        self.store_id        = store_id
        self.model_type      = model_type.lower()
        self.external_factors = external_factors or ExternalFactorsGenerator(seed=seed)
        self._meta           = _STORE_META.get(store_id, _STORE_META["CA_1"])
        self._baseline       = _StatisticalBaseline(store_id, base_demand=base_demand, seed=seed)

        # Rolling history: 60-day seed so lag features are valid on Day 0
        rng = np.random.RandomState(seed)
        self.history: list[float] = [max(0.0, base_demand + rng.normal(0, 1.5)) for _ in range(60)]
        self.demand_cache: dict[int, float] = {}

        self._model        = None
        self._feat_names: list[str] = []
        self._using_model  = False

        self._try_load_model()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _try_load_model(self) -> None:
        path = Path(MODEL_DIR) / f"lgb_model_{self.store_id}.bin"
        if not path.exists():
            path = Path(MODEL_DIR) / "lgb_model_CA_1.bin"  # graceful fallback
        try:
            import lightgbm as lgb
            self._model      = lgb.Booster(model_file=str(path))
            self._feat_names = self._model.feature_name()
            self._using_model = True
        except Exception as exc:
            warnings.warn(
                f"DemandGenerator[{self.store_id}]: could not load model ({exc}). "
                "Using statistical baseline."
            )

    # ------------------------------------------------------------------
    # Feature builder — all 35 features the trained model expects
    # ------------------------------------------------------------------

    def _build_row(self, date: datetime) -> "pd.DataFrame":
        """Build the exact 35-feature row matching the notebook's create_features()."""
        hist = self.history
        m    = self._meta
        sp   = m["sell_price"]
        wm_yr_wk = 11601 + (date - datetime(2016, 1, 4)).days // 7

        row = {
            "item_id": 1, "dept_id": 1, "cat_id": 1,
            "store_id":  m["store_id"],
            "state_id":  m["state_id"],
            "wm_yr_wk":  wm_yr_wk,
            "weekday":   date.weekday(),
            "wday":      date.weekday(),
            "month":     date.month,
            "year":      date.year,
            "event_name_1": -1, "event_type_1": -1,
            "event_name_2": -1, "event_type_2": -1,
            "snap_CA":   m["snap_CA"],
            "snap_TX":   m["snap_TX"],
            "snap_WI":   m["snap_WI"],
            "sell_price":          sp,
            "dayofweek":           date.weekday(),
            "day":                 date.day,
            "week":                date.isocalendar()[1],
            "quarter":             (date.month - 1) // 3 + 1,
            "sell_price_max":      sp,
            "sell_price_min":      sp * 0.92,
            "sell_price_std":      sp * 0.04,
            "sell_price_momentum": 1.0,
            # Lag features from rolling history
            "lag_7":  hist[-7],
            "lag_14": hist[-14],
            "lag_28": hist[-28],
            "rmean_28_7":  float(np.mean(hist[-35:-28])) if len(hist) >= 35 else float(np.mean(hist[-7:])),
            "rstd_28_7":   float(max(np.std(hist[-35:-28]), 0.1)) if len(hist) >= 35 else 0.1,
            "rmean_28_14": float(np.mean(hist[-42:-28])) if len(hist) >= 42 else float(np.mean(hist[-14:])),
            "rstd_28_14":  float(max(np.std(hist[-42:-28]), 0.1)) if len(hist) >= 42 else 0.1,
            "rmean_28_28": float(np.mean(hist[-56:-28])) if len(hist) >= 56 else float(np.mean(hist[-28:])),
            "rstd_28_28":  float(max(np.std(hist[-56:-28]), 0.1)) if len(hist) >= 56 else 0.1,
        }
        return pd.DataFrame([row])[self._feat_names]

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def _raw_predict(self, day_index: int) -> float:
        """Model prediction with smoothing, or statistical baseline."""
        date = _M5_BASE_DATE + timedelta(days=day_index + 1)

        if self._using_model and self._model is not None:
            try:
                row = self._build_row(date)
                raw = float(self._model.predict(row)[0])
                # Smooth to prevent recursive lag collapse
                smoothed = _SMOOTH_ALPHA * raw + (1.0 - _SMOOTH_ALPHA) * float(np.mean(self.history[-7:]))
                return max(0.0, smoothed)
            except Exception as exc:
                warnings.warn(f"DemandGenerator[{self.store_id}] predict failed: {exc}. Using baseline.")

        return self._baseline.predict(day_index, date)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_demand(self, day_index: int, category: str = "default") -> float:
        """Return demand for simulation day `day_index`.

        Applies ExternalFactors.demand_multiplier for holidays/weekends.
        Appends the result to rolling history so next call uses real data.
        """
        if day_index in self.demand_cache:
            return self.demand_cache[day_index]

        base   = self._raw_predict(day_index)
        date   = _M5_BASE_DATE + timedelta(days=day_index + 1)
        # Use .demand_multiplier attribute (ExternalFactors is a dataclass, not a method call)
        ext    = self.external_factors.generate(date)
        demand = base * ext.demand_multiplier

        final  = max(0.0, float(demand))

        # Append to rolling history for accurate lag features tomorrow
        self.history.append(final)
        self.demand_cache[day_index] = final
        return final

    def get_forecast_range(
        self,
        start_day: int,
        days: int = 14,
        category: str = "default",
    ) -> List[float]:
        """Return demand forecasts for `days` days starting at `start_day`."""
        return [self.get_demand(start_day + i, category=category) for i in range(days)]

    @property
    def using_trained_model(self) -> bool:
        """True if a real model artifact was loaded; False if using baseline."""
        return self._using_model