"""Proxy package so Streamlit can resolve `src.*` when launched from `src/dashboard`.

When Streamlit executes `src/dashboard/app.py` directly, it places `src/dashboard`
on `sys.path`. That means the real repository root package at `<repo>/src` is not
visible during import resolution. This shim exposes the real package directory as
the search path for `src`, without changing the actual project layout.
"""

from __future__ import annotations

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[2])]