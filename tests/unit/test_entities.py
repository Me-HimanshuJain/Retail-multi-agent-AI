import pytest
from src.simulation.entities import (
    Product, Store, Warehouse, Supplier, Shipment,
    InventoryBatch, SimulationDailyMetrics, SimulationRunMetrics,
    SimulationState
)

def test_product_margin():
    p1 = Product(product_id=1, name="A", unit_cost=1.0, base_price=2.0, shelf_life_days=10)
    assert p1.margin == 0.5
    
    p2 = Product(product_id=2, name="B", unit_cost=1.0, base_price=0.0, shelf_life_days=10)
    assert p2.margin == 0.0

def test_store_inventory():
    s = Store(1, "S1", "R1", 100, 0.0, 0.0)
    s.update_stock(100, 5)
    assert s.get_stock(100) == 5
    s.update_stock(100, -2)
    assert s.get_stock(100) == 3
    s.update_stock(100, -5) # should not drop below 0
    assert s.get_stock(100) == 0
    assert s.get_stock(999) == 0

def test_warehouse_inventory():
    w = Warehouse(1, "W1", "hub", 10, 0.0, 0.0)
    w.update_stock(100, 5)
    assert w.inventory[100] == 5
    w.update_stock(100, -2)
    assert w.inventory[100] == 3
    w.update_stock(100, -5) # should not drop below 0
    assert w.inventory[100] == 0

def test_warehouse_utilization():
    w = Warehouse(1, "W1", "hub", 10, 0.0, 0.0)
    assert w.current_utilization == 0.0
    w.update_stock(100, 5)
    assert w.current_utilization == 0.5
    assert w.can_accept(5) is True
    assert w.can_accept(6) is False
    
    w_zero = Warehouse(2, "W2", "hub", 0, 0.0, 0.0)
    assert w_zero.current_utilization == 0.0

def test_supplier_reliability():
    sup = Supplier(1, "Sup", 0.8, 2)
    assert sup.observed_reliability == 0.8
    sup.record_order_result(True)
    assert sup.observed_reliability == 1.0
    sup.record_order_result(False)
    assert sup.observed_reliability == 0.5

def test_shipment_tracking():
    ship = Shipment("id1", 100, 10, "A", "B", scheduled_arrival_day=5)
    assert not ship.on_time
    ship.mark_delivered(4)
    assert ship.delivered
    assert not ship.delayed
    assert ship.on_time
    
    ship2 = Shipment("id2", 100, 10, "A", "B", scheduled_arrival_day=5)
    ship2.mark_delivered(6)
    assert ship2.delayed
    assert ship2.delay_days == 1
    assert not ship2.on_time

def test_inventory_batch():
    b = InventoryBatch(100, 10, receive_day=2, shelf_life_days=5)
    assert b.expiry_day == 7
    assert b.units_expired_on_day(6) == 0
    assert b.units_expired_on_day(7) == 10
    assert b.units_expired_on_day(7) == 0 # already expired

def test_run_metrics_empty():
    run = SimulationRunMetrics.from_daily([], 0.0)
    assert run.days_simulated == 0

def test_simulation_state():
    state = SimulationState()
    assert state.on_time_delivery_rate == 1.0 # default empty
    
    ship = Shipment("id1", 100, 10, "A", "B", scheduled_arrival_day=5)
    state.record_shipment(ship)
    assert len(state.pending_shipments) == 1
    
    arrived = state.process_arrivals(5)
    assert len(arrived) == 1
    assert len(state.pending_shipments) == 0
    assert len(state.delivered_shipments) == 1
    assert state.on_time_delivery_rate == 1.0
    
    # delayed shipment
    ship2 = Shipment("id2", 100, 10, "A", "B", scheduled_arrival_day=5)
    state.record_shipment(ship2)
    state.process_arrivals(6) # late
    assert state.on_time_delivery_rate == 0.5
