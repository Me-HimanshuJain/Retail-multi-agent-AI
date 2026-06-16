import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.core.event_bus import EventBus, EventBusConfig, DeadLetterQueue, get_event_bus, publish_event, close_event_bus
from src.core.events import RestockRequest

@pytest.fixture
def test_event():
    return RestockRequest(
        agent_id="test_agent",
        product_id=123,
        location_type="store",
        location_id=1,
        quantity=100
    )

@pytest.mark.asyncio
async def test_dead_letter_queue_add(test_event):
    dlq = DeadLetterQueue()
    dlq.add("test_stream", test_event, "Test error")
    assert len(dlq.messages) == 1
    assert dlq.messages[0]["stream"] == "test_stream"
    assert dlq.messages[0]["event_type"] == "RestockRequest"
    assert dlq.messages[0]["error"] == "Test error"

@pytest.mark.asyncio
async def test_event_bus_connect_no_redis():
    with patch("src.core.event_bus.redis", None):
        bus = EventBus()
        await bus.connect()
        assert bus._client is None

@pytest.mark.asyncio
async def test_event_bus_publish_no_redis(test_event):
    with patch("src.core.event_bus.redis", None):
        bus = EventBus()
        result = await bus.publish("test_stream", test_event)
        assert result == test_event.event_id

@pytest.mark.asyncio
async def test_event_bus_publish_with_redis(test_event):
    mock_redis = AsyncMock()
    mock_redis.xadd.return_value = "12345-0"
    
    with patch("src.core.event_bus.redis") as mock_redis_module:
        mock_redis_module.Redis.return_value = mock_redis
        
        bus = EventBus()
        result = await bus.publish("test_stream", test_event)
        
        assert result == "12345-0"
        mock_redis.xadd.assert_called_once()
        args, kwargs = mock_redis.xadd.call_args
        assert args[0] == "test_stream"
        assert "event_json" in args[1]

@pytest.mark.asyncio
async def test_event_bus_close():
    mock_redis = AsyncMock()
    
    with patch("src.core.event_bus.redis") as mock_redis_module:
        mock_redis_module.Redis.return_value = mock_redis
        
        bus = EventBus()
        await bus.connect()
        await bus.close()
        
        mock_redis.close.assert_called_once()
        assert bus._client is None

@pytest.mark.asyncio
async def test_global_get_event_bus():
    # Ensure isolation from other tests
    with patch("src.core.event_bus._default_bus", None):
        bus = await get_event_bus()
        assert isinstance(bus, EventBus)
        
        # Subsequent calls should return the same instance
        bus2 = await get_event_bus()
        assert bus is bus2

@pytest.mark.asyncio
async def test_global_publish_event(test_event):
    with patch("src.core.event_bus._default_bus", None):
        with patch("src.core.event_bus.EventBus.publish", new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = "msg-id"
            result = await publish_event("test_stream", test_event)
            assert result == "msg-id"
            mock_publish.assert_called_once_with("test_stream", test_event)

@pytest.mark.asyncio
async def test_global_close_event_bus():
    with patch("src.core.event_bus._default_bus", None):
        bus = await get_event_bus()
        with patch.object(bus, "close", new_callable=AsyncMock) as mock_close:
            await close_event_bus()
            mock_close.assert_called_once()
