"""Typed events for inter-agent communication."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = Field(default="BaseEvent")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "BaseEvent":
        return cls.model_validate_json(data)


class DemandForecastUpdated(BaseEvent):
    event_type: str = Field(default="DemandForecastUpdated")
    product_id: int
    store_id: int
    horizon: int
    forecasts: Dict[str, List[float]]


class RestockRequest(BaseEvent):
    event_type: str = Field(default="RestockRequest")
    product_id: int
    location_type: str
    location_id: int
    quantity: int


EVENT_REGISTRY: Dict[str, Type[BaseEvent]] = {
    "DemandForecastUpdated": DemandForecastUpdated,
    "RestockRequest": RestockRequest,
}


def deserialize_event(data: Dict[str, Any] | str) -> Optional[BaseEvent]:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None
    event_type = data.get("event_type")
    model = EVENT_REGISTRY.get(event_type)
    if not model:
        return None
    return model.model_validate(data)


def get_event_schema(event_type: str) -> Optional[Type[BaseEvent]]:
    return EVENT_REGISTRY.get(event_type)


def list_event_types() -> List[str]:
    return sorted(EVENT_REGISTRY.keys())
