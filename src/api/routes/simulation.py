"""Simulation routes."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import User, operator_required
from src.core.config import yaml_config
from src.simulation.environment import RetailSimulator

router = APIRouter(prefix="/simulation", tags=["Simulation"])

_current_simulation: Optional[RetailSimulator] = None
_simulation_status: dict = {"running": False, "simulation_id": None, "days": 0}


class SimulationStartRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    seed: int = Field(default=42)
    inject_disruptions: bool = Field(default=False)


class SimulationStartResponse(BaseModel):
    simulation_id: str
    status: str
    days: int


class SimulationStatus(BaseModel):
    running: bool
    simulation_id: Optional[str] = None
    total_days: Optional[int] = None


class SimulationMetrics(BaseModel):
    total_revenue: float
    total_profit: float
    fill_rate: float
    stockout_rate: float
    on_time_delivery_rate: float


class DisruptionRequest(BaseModel):
    type: str
    severity: str = "medium"
    params: dict = Field(default_factory=dict)


async def _run_simulation_task(sim: RetailSimulator, days: int):
    await sim.run(days)
    _simulation_status.update({"running": False, "total_days": days})


@router.post("/start")
async def start_simulation(request: SimulationStartRequest, current_user: User = Depends(operator_required)) -> SimulationStartResponse:
    global _current_simulation
    _simulation_status.update({"running": True, "simulation_id": "sim-001", "days": request.days})
    _current_simulation = RetailSimulator(seed=request.seed)
    asyncio.create_task(_run_simulation_task(_current_simulation, request.days))
    return SimulationStartResponse(simulation_id="sim-001", status="started", days=request.days)


@router.get("/status")
async def get_simulation_status() -> SimulationStatus:
    return SimulationStatus(**_simulation_status)


@router.get("/metrics")
async def get_simulation_metrics() -> SimulationMetrics:
    if not _current_simulation:
        raise HTTPException(status_code=404, detail="No simulation available")
    return SimulationMetrics(total_revenue=0.0, total_profit=0.0, fill_rate=0.0, stockout_rate=0.0, on_time_delivery_rate=0.0)


@router.post("/disrupt")
async def inject_disruption(request: DisruptionRequest, current_user: User = Depends(operator_required)) -> dict:
    return {"status": "queued", "type": request.type, "severity": request.severity}
