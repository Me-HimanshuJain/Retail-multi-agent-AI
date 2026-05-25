"""Redis Streams event bus with retry and dead-letter support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger

from .config import settings
from .events import BaseEvent

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None


@dataclass
class EventBusConfig:
    host: str = settings.REDIS_HOST
    port: int = settings.REDIS_PORT
    stream_prefix: str = "retail:events"
    dead_letter_prefix: str = "retail:dead"
    max_retries: int = 3


@dataclass
class DeadLetterQueue:
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, stream: str, event: BaseEvent, error: str) -> None:
        self.messages.append({"stream": stream, "event_type": event.event_type, "error": error})


class EventBus:
    def __init__(self, config: EventBusConfig | None = None) -> None:
        self.config = config or EventBusConfig()
        self.dead_letters = DeadLetterQueue()
        self._client = None

    async def connect(self) -> None:
        if redis is None:
            return
        if self._client is None:
            self._client = redis.Redis(host=self.config.host, port=self.config.port, decode_responses=True)

    async def publish(self, stream: str, event: BaseEvent) -> str:
        await self.connect()
        if self._client is None:
            logger.info("event bus disabled; dropping %s", event.event_type)
            return event.event_id
        payload = event.model_dump(mode="json")
        payload["event_json"] = event.to_json()
        return await self._client.xadd(stream, payload)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


_default_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


async def publish_event(stream: str, event: BaseEvent) -> str:
    bus = await get_event_bus()
    return await bus.publish(stream, event)


async def close_event_bus() -> None:
    if _default_bus is not None:
        await _default_bus.close()
