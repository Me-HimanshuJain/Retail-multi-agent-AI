"""Unified LightGBM model I/O — handles both native and joblib-serialised Boosters.

Background
----------
LightGBM models in this project were saved using ``joblib.dump(booster, path)``.
However, ``lgb.Booster(model_file=path)`` expects LightGBM's own native text
format (the output of ``booster.save_model()``).  Loading a joblib pickle with
the native reader raises::

    LightGBMError: Unknown model format or submodel type

``load_lgbm_booster()`` transparently handles both formats so all call-sites
stay simple and forward-compatible with either save strategy.
"""

from __future__ import annotations

import joblib
from pathlib import Path

from lightgbm import Booster
from lightgbm.basic import LightGBMError


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
