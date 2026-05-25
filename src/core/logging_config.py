"""Logging setup."""

from __future__ import annotations

import logging
from logging.config import dictConfig


def setup_logging(config: dict | None = None) -> None:
    if config:
        dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)
