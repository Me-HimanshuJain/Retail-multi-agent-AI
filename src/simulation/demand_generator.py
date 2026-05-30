"""Demand generator — bridges trained model artifacts to the simulation loop.

This is the file that was missing entirely from the repo.
environment.py imports DemandGenerator from here.

Design:
- Loads a trained LightGBM or XGBoost model artifact from disk.
- Falls back to a realistic statistical baseline (Poisson + trend) if no
  artifact is found, so the simulation still runs without trained models.
- Applies ExternalFactors multipliers so holidays/weekends/weather affect demand.
- Exposes get_demand(day) and get_forecast_range(day, days) used by
  SmartInventoryAgent.
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import numpy as np

from src.simulation.external_factors import ExternalFactorsGenerator

# ---------------------------------------------------------------------------
# Model artifact paths — adjust MODEL_DIR if your layout differs
# ---------------------------------------------------------------------------
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))

LGBM_PATTERN = "lgb_model_{store_id}.bin"
XGB_PATTERN  = "xgb_model_{store_id}.json"


def _load_lgbm(path: Path):
    """Load a LightGBM Booster from a .bin artifact."""
    try:
        import lightgbm as lgb  # type: ignore
        return lgb.Booster(model_file=str(path))
    except Exception as exc:
        warnings.warn(f"DemandGenerator: failed to load LightGBM from {path}: {exc}")
        return None


def _load_xgb(path: Path):
    """Load an XGBoost Booster from a .json artifact."""
    try:
        import xgboost as xgb  # type: ignore
        booster = xgb.Booster()
        booster.load_model(str(path))
        return booster
    except Exception as exc:
        warnings.warn(f"DemandGenerator: failed to load XGBoost from {path}: {exc}")
        return None


def _build_features(day_index: int, date: datetime) -> np.ndarray:
    """Build a minimal feature vector that mirrors the training feature set.

    Matches the features used in src/models/forecasting/training.py.
    Extend this to match your actual feature engineering if richer features
    were used during training.

    Features (in order):
        0  day_of_week        (0=Mon … 6=Sun)
        1  day_of_month       (1-31)
        2  month              (1-12)
        3  week_of_year       (1-53)
        4  is_weekend         (0/1)
        5  is_month_start     (0/1)
        6  is_month_end       (0/1)
        7  quarter            (1-4)
        8  day_index          (simulation day number — encodes trend)
        9  sin_day_of_year    (annual seasonality)
        10 cos_day_of_year    (annual seasonality)
        11 sin_week           (weekly seasonality)
        12 cos_week           (weekly seasonality)
    """
    dow        = date.weekday()
    dom        = date.day
    month      = date.month
    woy        = date.isocalendar()[1]
    is_weekend = int(dow >= 5)
    is_ms      = int(dom == 1)
    is_me      = int(dom == (date.replace(month=month % 12 + 1, day=1) - timedelta(days=1)).day)
    quarter    = (month - 1) // 3 + 1
    doy        = date.timetuple().tm_yday
    sin_doy    = np.sin(2 * np.pi * doy / 365.25)
    cos_doy    = np.cos(2 * np.pi * doy / 365.25)
    sin_week   = np.sin(2 * np.pi * dow / 7)
    cos_week   = np.cos(2 * np.pi * dow / 7)

    return np.array([[
        dow, dom, month, woy, is_weekend, is_ms, is_me,
        quarter, day_index, sin_doy, cos_doy, sin_week, cos_week,
    ]], dtype=np.float32)


class _StatisticalBaseline:
    """Realistic fallback when no model artifact is available.

    Uses a Poisson process with:
    - A gentle upward trend (0.1 % per day)
    - Weekly seasonality (weekends +15 %)
    - Annual seasonality (Dec/Jan +20 %)
    - Per-store randomisation seeded reproducibly
    """
    def __init__(self, store_id: str, base_demand: float = 35.0, seed: int = 42):
        store_hash = hash(store_id) % (2 ** 31)
        self.rng = np.random.default_rng(seed ^ store_hash)
        self.base = base_demand

    def predict(self, day_index: int, date: datetime) -> float:
        trend    = 1.0 + 0.001 * day_index
        dow      = date.weekday()
        weekend  = 1.15 if dow >= 5 else 1.0
        month    = date.month
        seasonal = 1.20 if month in (11, 12, 1) else (0.90 if month in (6, 7) else 1.0)
        mu       = self.base * trend * weekend * seasonal
        return float(self.rng.poisson(max(1.0, mu)))


class DemandGenerator:
    """Load a trained model artifact and produce per-day demand for one store.

    Parameters
    ----------
    store_id : str
        Store string name as used in the model artifact filename,
        e.g. "CA_1" -> lgb_model_CA_1.bin
    model_type : str
        "lgbm" (default) or "xgb"
    external_factors : ExternalFactorsGenerator
        Shared instance from the simulator — used to retrieve demand multipliers.
    start_date : datetime
        The calendar date corresponding to simulation day 0.
        Defaults to today if not provided.
    seed : int
        For the statistical fallback only.
    base_demand : float
        Fallback baseline demand per day (units).
    """

    def __init__(
        self,
        store_id: str,
        model_type: str = "lgbm",
        external_factors: Optional[ExternalFactorsGenerator] = None,
        start_date: Optional[datetime] = None,
        seed: int = 42,
        base_demand: float = 35.0,
    ) -> None:
        self.store_id = store_id
        self.model_type = model_type.lower()
        self.external_factors = external_factors or ExternalFactorsGenerator(seed=seed)
        self.start_date = start_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._model = None
        self._baseline = _StatisticalBaseline(store_id, base_demand=base_demand, seed=seed)
        self._using_model = False

        self._try_load_model()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_load_model(self) -> None:
        if self.model_type == "lgbm":
            path = MODEL_DIR / LGBM_PATTERN.format(store_id=self.store_id)
            if path.exists():
                m = _load_lgbm(path)
                if m is not None:
                    self._model = m
                    self._using_model = True
                    return
        elif self.model_type == "xgb":
            path = MODEL_DIR / XGB_PATTERN.format(store_id=self.store_id)
            if path.exists():
                m = _load_xgb(path)
                if m is not None:
                    self._model = m
                    self._using_model = True
                    return
        # No artifact found — will use statistical baseline
        warnings.warn(
            f"DemandGenerator[{self.store_id}]: no {self.model_type} artifact found at "
            f"{MODEL_DIR}. Using statistical baseline."
        )

    def _date_for_day(self, day_index: int) -> datetime:
        return self.start_date + timedelta(days=day_index)

    def _raw_predict(self, day_index: int) -> float:
        """Return raw model or baseline prediction (no external factor applied)."""
        date = self._date_for_day(day_index)
        if self._using_model and self._model is not None:
            features = _build_features(day_index, date)
            try:
                if self.model_type == "lgbm":
                    pred = self._model.predict(features)
                else:
                    import xgboost as xgb  # type: ignore
                    dmat = xgb.DMatrix(features)
                    pred = self._model.predict(dmat)
                return float(max(0.0, pred[0]))
            except Exception as exc:
                warnings.warn(f"DemandGenerator[{self.store_id}] predict failed: {exc}. Using baseline.")
        return self._baseline.predict(day_index, date)

    # ------------------------------------------------------------------
    # Public API (called by SmartInventoryAgent and the simulation loop)
    # ------------------------------------------------------------------

    def get_demand(self, day_index: int, category: str = "default") -> float:
        """Return expected demand for simulation day *day_index*.

        Applies ExternalFactors category multiplier so holidays / weather
        are reflected in the returned value.
        """
        date = self._date_for_day(day_index)
        raw = self._raw_predict(day_index)
        factors = self.external_factors.generate(date)
        multiplier = factors.get_demand_multiplier(category)
        return raw * multiplier

    def get_forecast_range(
        self,
        start_day: int,
        days: int = 14,
        category: str = "default",
    ) -> List[float]:
        """Return a list of demand forecasts for *days* days starting at *start_day*.

        Used by SmartInventoryAgent to compute reorder quantities.
        """
        return [self.get_demand(start_day + i, category=category) for i in range(days)]

    @property
    def using_trained_model(self) -> bool:
        """True if a real model artifact was loaded; False if using baseline."""
        return self._using_model