"""Health endpoints."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }


@router.get("/health/detailed")
async def detailed_health() -> dict:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


@router.get("/health/ready")
async def readiness_probe() -> dict:
    return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/live")
async def liveness_probe() -> dict:
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}
