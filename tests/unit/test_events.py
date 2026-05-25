from __future__ import annotations

from src.core.events import DemandForecastUpdated, RestockRequest, deserialize_event, list_event_types


def test_event_round_trip():
    event = DemandForecastUpdated(agent_id="a", product_id=1, store_id=2, horizon=7, forecasts={"median": [1.0]})
    restored = deserialize_event(event.to_json())
    assert restored is not None
    assert restored.event_type == "DemandForecastUpdated"


def test_event_registry():
    assert "RestockRequest" in list_event_types()
