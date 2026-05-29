"""Demand generation using trained LightGBM models with rolling history."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.simulation.external_factors import ExternalFactorsGenerator

# Last training day in M5 = d_1941 = 2016-05-22
_M5_BASE_DATE = datetime(2016, 5, 22)

# Store metadata: encoded exactly as notebook's create_features() label-encoding
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

_SMOOTH_ALPHA = 0.35   # blend raw prediction with recent history to prevent lag collapse


class DemandGenerator:
    """Generate realistic daily demand using a trained LightGBM store model.

    Rolling history approach (from your Copilot version — this is correct):
    - Initialises 60 days of seeded history so lag features are valid on Day 0.
    - Appends each generated demand value to history so tomorrow's features
      are computed from real simulation history, not constants.
    - Uses exponential smoothing to prevent the recursive-lag collapse problem.
    """

    def __init__(
        self,
        store_id: str,
        model_type: str = "lgbm",
        model_dir: str | Path = "models",
        external_factors: Optional[ExternalFactorsGenerator] = None,
        seed: int = 42,
        initial_lag: float = 10.0,
    ):
        self.store_id    = store_id
        self.model_dir   = Path(model_dir)
        self.rng         = np.random.RandomState(seed)
        self.external_factors = external_factors or ExternalFactorsGenerator(seed=seed)
        self._meta       = _STORE_META.get(store_id, _STORE_META["CA_1"])
        self._initial_lag = initial_lag

        # Rolling demand history — 60-day seed so lag_28+rolling windows are valid immediately
        self.history: list[float] = [
            max(0.0, initial_lag + self.rng.normal(0, 1.5)) for _ in range(60)
        ]
        self.demand_cache: dict[int, float] = {}

        self.model = None
        self._feature_names: list[str] = []
        self._load_model()

    # ------------------------------------------------------------------
    # Model loading — guarded imports so missing modules don't crash
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        try:
            import lightgbm as lgb
            path = self.model_dir / f"lgb_model_{self.store_id}.bin"
            if not path.exists():
                path = self.model_dir / "lgb_model_CA_1.bin"   # fallback
            self.model = lgb.Booster(model_file=str(path))
            self._feature_names = self.model.feature_name()
        except Exception as exc:
            print(f"Warning: could not load LightGBM model for {self.store_id}: {exc}")
            self.model = None

    # ------------------------------------------------------------------
    # Feature builder — all 35 features the model expects
    # ------------------------------------------------------------------

    def _build_row(self, date: datetime) -> "pd.DataFrame":
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
            "sell_price":         sp,
            "dayofweek":          date.weekday(),
            "day":                date.day,
            "week":               date.isocalendar()[1],
            "quarter":            (date.month - 1) // 3 + 1,
            "sell_price_max":     sp,
            "sell_price_min":     sp * 0.92,
            "sell_price_std":     sp * 0.04,
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
        return pd.DataFrame([row])[self._feature_names]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_demand(self, day_index: int, price_delta_pct: float = 0.0) -> float:
        """Return demand for simulation day `day_index` (0-based)."""
        if day_index in self.demand_cache:
            return self.demand_cache[day_index]

        # 1. Model prediction with full 35-feature row
        if self.model is not None:
            try:
                date = _M5_BASE_DATE + timedelta(days=day_index + 1)
                row  = self._build_row(date)
                raw  = float(self.model.predict(row)[0])
                # Smooth to prevent recursive lag collapse
                base = _SMOOTH_ALPHA * raw + (1 - _SMOOTH_ALPHA) * float(np.mean(self.history[-7:]))
            except Exception:
                base = float(np.mean(self.history[-7:]))
        else:
            base = float(np.mean(self.history[-7:]))

        base = max(0.0, base)

        # 2. External factors (holidays, weekends)
        current_date = _M5_BASE_DATE + timedelta(days=day_index + 1)
        ext    = self.external_factors.generate(current_date)
        demand = base * ext.demand_multiplier

        # 3. Customer noise ±15%
        demand *= self.rng.normal(1.0, 0.15)

        # 4. Price elasticity
        if price_delta_pct != 0.0:
            demand *= 1.0 + (price_delta_pct / 100.0) * (-1.5 / 100.0)

        final = max(0.0, float(demand))

        # Append to rolling history so next call uses real simulation data
        self.history.append(final)
        self.demand_cache[day_index] = final
        return final

    def get_forecast_range(self, start_day: int, days: int = 28) -> list[float]:
        return [self.get_demand(start_day + i) for i in range(days)]