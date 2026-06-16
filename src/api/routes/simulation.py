"""Simulation API routes."""

import asyncio
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import User, any_authenticated, operator_required
from src.simulation.environment import RetailSimulator

router = APIRouter(prefix="/simulation", tags=["Simulation"])

_current_simulation: Optional[RetailSimulator] = None
_simulation_status: dict = {"running": False, "simulation_id": None, "total_days": 0}


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
    service_level: Optional[float] = None
    waste_rate: Optional[float] = None
    inventory_turnover: Optional[float] = None


class DisruptionRequest(BaseModel):
    type: str
    severity: str = "medium"
    params: dict = Field(default_factory=dict)


async def _run_simulation_task(sim: RetailSimulator, days: int) -> None:
    await sim.run(days)
    _simulation_status.update({"running": False, "total_days": days})


@router.post("/start")
async def start_simulation(
    request: SimulationStartRequest,
    _current_user: User = Depends(operator_required),
) -> SimulationStartResponse:
    """Start a new simulation. Requires operator or admin role."""
    global _current_simulation

    sim_id = str(uuid4())
    _simulation_status.update({
        "running": True,
        "simulation_id": sim_id,
        "total_days": request.days,
    })

    _current_simulation = RetailSimulator(seed=request.seed)
    asyncio.create_task(_run_simulation_task(_current_simulation, request.days))

    return SimulationStartResponse(simulation_id=sim_id, status="started", days=request.days)


@router.get("/status")
async def get_simulation_status(
    _current_user: User = Depends(any_authenticated),
) -> SimulationStatus:
    """Get current simulation status. Requires authentication."""
    return SimulationStatus(**_simulation_status)


@router.get("/metrics")
async def get_simulation_metrics(
    _current_user: User = Depends(any_authenticated),
) -> SimulationMetrics:
    """Get current simulation metrics. Requires authentication."""
    if _current_simulation is None:
        raise HTTPException(status_code=404, detail="No simulation has been started yet.")

    raw = _current_simulation.get_metrics()
    return SimulationMetrics(
        total_revenue         = raw.get("total_revenue", 0.0),
        total_profit          = raw.get("total_profit",  0.0),
        fill_rate             = raw.get("fill_rate",     0.0),
        stockout_rate         = raw.get("stockout_rate", 0.0),
        on_time_delivery_rate = raw.get("on_time_delivery_rate", 0.95),
        service_level         = raw.get("service_level"),
        waste_rate            = raw.get("waste_rate"),
        inventory_turnover    = raw.get("inventory_turnover"),
    )


@router.post("/disrupt")
async def inject_disruption(
    request: DisruptionRequest,
    _current_user: User = Depends(operator_required),
) -> dict:
    """Inject a disruption into the running simulation. Requires operator or admin role."""
    global _current_simulation
    if not _current_simulation:
        raise HTTPException(status_code=400, detail="No active simulation running.")

    _current_simulation.inject_disruption(request.type, request.severity)
    return {"status": "injected", "type": request.type, "severity": request.severity}