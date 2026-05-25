"""Shared test fixtures."""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    return TestClient(app)
