"""Unified model I/O and feature alignment for LightGBM and XGBoost artifacts.

Background
----------
Models in ``models/`` were saved by different training scripts that used
different feature engineering pipelines.  The current ``engineer_features()``
pipeline produces 35 columns; the LightGBM artifacts expect 32 (with legacy
names); the XGBoost artifacts expect 40 (with even more divergent names and
engineered boolean columns).

This module provides:

* ``load_lgbm_booster()``  — loads ``.bin`` artifacts regardless of whether
  they were saved via ``booster.save_model()`` (native text) or
  ``joblib.dump(booster)`` (pickle).

* ``align_features_to_model()`` — maps a current-pipeline DataFrame to exactly
  the feature set a LightGBM Booster was trained on.

* ``align_features_to_xgb()``   — same for a native XGBoost Booster, including
  synthetic reconstruction of boolean / rolling features the current pipeline
  does not produce.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from lightgbm import Booster
from lightgbm.basic import LightGBMError


# ---------------------------------------------------------------------------
# LightGBM loader
# ---------------------------------------------------------------------------

def load_lgbm_booster(path: str | Path) -> Booster:
    """Load a LightGBM Booster from a native ``save_model`` file or a joblib dump.

    Try 1 — native LightGBM text format (produced by ``booster.save_model()``).
    Try 2 — joblib pickle of a ``lightgbm.basic.Booster``.
    Try 3 — joblib pickle of a ``LGBMRegressor`` sklearn wrapper (reads ``.booster_``).

    Parameters
    ----------
    path : str | Path
        Path to the ``.bin`` model artifact.

    Returns
    -------
    lightgbm.basic.Booster
        The loaded Booster, ready for ``.predict()``.

    Raises
    ------
    FileNotFoundError
        If the artifact does not exist at *path*.
    ValueError
        If the file exists but cannot be loaded by either method.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"LightGBM artifact not found: {path}")

    # --- Attempt 1: native LightGBM text format ---
    try:
        return Booster(model_file=str(path))
    except LightGBMError:
        pass  # file is not in native format; try joblib

    # --- Attempt 2 & 3: joblib-serialised object ---
    try:
        obj = joblib.load(path)
    except Exception as exc:
        raise ValueError(
            f"Failed to load LightGBM artifact from {path}: "
            f"not a native model file and joblib.load() raised {exc}"
        ) from exc

    if isinstance(obj, Booster):
        return obj

    # Handle full LGBMRegressor saved by sklearn API
    if hasattr(obj, "booster_") and isinstance(obj.booster_, Booster):
        return obj.booster_

    raise ValueError(
        f"joblib payload at {path} is {type(obj).__name__!r}; "
        f"expected lightgbm.basic.Booster or an LGBMRegressor with .booster_"
    )


# ---------------------------------------------------------------------------
# Feature alignment — LightGBM
# ---------------------------------------------------------------------------

# Canonical map: current engineer_features() column name  →  legacy model name.
# Extend this table whenever a column is renamed in the pipeline without
# retraining the model artifacts.
_LGB_RENAME_ALIASES: dict[str, str] = {
    "day":                 "mday",
    "sell_price_max":      "price_max",
    "sell_price_min":      "price_min",
    "sell_price_std":      "price_std",
    "sell_price_momentum": "price_momentum",
}


def align_features_to_model(df: pd.DataFrame, booster: Booster) -> pd.DataFrame:
    """Return a copy of *df* with exactly the columns the LightGBM Booster expects.

    Steps
    -----
    1. Apply ``_LGB_RENAME_ALIASES`` to map current pipeline names to legacy names.
    2. Select only ``booster.feature_name()`` columns in the correct order.
    3. Raise ``KeyError`` with a diagnostic message if any column is still missing.

    Parameters
    ----------
    df : pd.DataFrame
        Feature DataFrame from the current ``engineer_features()`` pipeline.
    booster : lightgbm.basic.Booster
        The loaded Booster whose stored feature list is authoritative.

    Returns
    -------
    pd.DataFrame
        DataFrame with exactly the columns and order the Booster expects.
    """
    required = booster.feature_name()
    rename = {cur: leg for cur, leg in _LGB_RENAME_ALIASES.items() if cur in df.columns}
    aligned = df.rename(columns=rename)
    missing = [f for f in required if f not in aligned.columns]
    if missing:
        raise KeyError(
            f"align_features_to_model: {len(missing)} feature(s) required by the "
            f"LightGBM model are absent even after aliasing.\n"
            f"Missing: {missing}\n"
            f"Available: {sorted(aligned.columns.tolist())}\n"
            f"Hint: add an entry to lgbm_io._LGB_RENAME_ALIASES or retrain."
        )
    return aligned[required]


# ---------------------------------------------------------------------------
# Feature alignment — XGBoost
# ---------------------------------------------------------------------------

# Rename map: current pipeline name → legacy XGBoost feature name.
_XGB_RENAME_ALIASES: dict[str, str] = {
    "day":                 "mday",
    "sell_price_max":      "price_max",
    "sell_price_min":      "price_min",
    "sell_price_std":      "price_std",
    "sell_price_momentum": "price_momentum",
}

# Features the XGBoost models expect that the current pipeline does not produce.
# Values are computed from existing pipeline columns where possible; otherwise
# filled with 0.0 (a safe neutral for boolean and ratio features).
_XGB_SYNTHETIC_FEATURES = {
    # Boolean flags derivable from pipeline columns
    "is_weekend":         lambda df: ((df["wday"] if "wday" in df.columns else df.get("dayofweek", 0)) >= 5).astype(float),
    "is_snap":            lambda df: (
        df.get("snap_CA", 0) | df.get("snap_TX", 0) | df.get("snap_WI", 0)
    ).astype(float),
    "is_event_1":         lambda df: (df.get("event_name_1", -1) != -1).astype(float),
    "is_event_2":         lambda df: (df.get("event_name_2", -1) != -1).astype(float),
    # One-hot event type flags (encoded from event_type_* integer codes)
    "event_type_cultural":  lambda df: (df.get("event_type_1", -1) == 0).astype(float),
    "event_type_national":  lambda df: (df.get("event_type_1", -1) == 1).astype(float),
    "event_type_religious": lambda df: (df.get("event_type_1", -1) == 2).astype(float),
    "event_type_sporting":  lambda df: (df.get("event_type_1", -1) == 3).astype(float),
    # Additional lags and rolling stats not in current pipeline
    "lag_21":             lambda df: df.get("lag_14", 0.0),   # approximate with lag_14
    "lag_56":             lambda df: df.get("lag_28", 0.0),   # approximate with lag_28
    "rmean_7_7":          lambda df: df.get("rmean_28_7", 0.0),
    "rmean_7_14":         lambda df: df.get("rmean_28_14", 0.0),
    "rmean_7_28":         lambda df: df.get("rmean_28_28", 0.0),
    "rstd_7_7":           lambda df: df.get("rstd_28_7", 0.0),
    "rstd_7_14":          lambda df: df.get("rstd_28_14", 0.0),
    "rstd_7_28":          lambda df: df.get("rstd_28_28", 0.0),
    # Price features (zero-fill where unavailable)
    "price_norm":         lambda df: 0.0,
    "price_pct_change":   lambda df: 0.0,
}


def align_features_to_xgb(df: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    """Return a copy of *df* with exactly the columns the XGBoost model expects.

    For features the current pipeline does not produce, synthetic approximations
    are computed from available pipeline columns (see ``_XGB_SYNTHETIC_FEATURES``).
    Boolean/ratio features with no approximation are zero-filled.

    Parameters
    ----------
    df : pd.DataFrame
        Feature DataFrame from the current ``engineer_features()`` pipeline.
    feature_names : list[str]
        The authoritative feature list from ``xgb.Booster().feature_names``.

    Returns
    -------
    pd.DataFrame
        DataFrame with exactly ``feature_names`` columns in the correct order.
    """
    # Apply rename aliases first
    rename = {cur: leg for cur, leg in _XGB_RENAME_ALIASES.items() if cur in df.columns}
    aligned = df.rename(columns=rename).copy()

    # Synthesise any missing features
    for feat in feature_names:
        if feat not in aligned.columns:
            if feat in _XGB_SYNTHETIC_FEATURES:
                try:
                    val = _XGB_SYNTHETIC_FEATURES[feat](aligned)
                    aligned[feat] = val
                except Exception:
                    aligned[feat] = 0.0
            else:
                aligned[feat] = 0.0  # unknown feature — safe neutral

    missing = [f for f in feature_names if f not in aligned.columns]
    if missing:
        raise KeyError(
            f"align_features_to_xgb: {len(missing)} feature(s) still missing "
            f"after aliasing and synthesis: {missing}"
        )
    return aligned[feature_names]
