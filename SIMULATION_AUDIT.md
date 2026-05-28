# Simulation Audit - Phase 4

**Date**: 2026-05-29  
**Status**: Identifies critical placeholders and real requirements  
**Purpose**: Map current synthetic simulation to production-ready event-driven system using real forecasts

---

## Executive Summary

Current simulation layer uses **hardcoded KPIs, constant demand, no forecast integration, no inventory depletion, and no supplier modeling**. This audit identifies 14 critical components requiring replacement or implementation.

### Critical Issues
1. ❌ Revenue/profit hardcoded to increment by fixed amounts
2. ❌ No actual inventory depletion based on demand
3. ❌ Fill rate hardcoded to 0.95 (never recalculated)
4. ❌ External factors generated but unused
5. ❌ Demand completely synthetic (not forecast-based)
6. ❌ Supplier delays not simulated
7. ❌ Pricing logic absent
8. ❌ Stockout/waste calculations incorrect
9. ❌ No customer behavior modeling
10. ❌ API returns hardcoded metric zeros
11. ❌ Dashboard shows placeholder data
12. ❌ No event emission during simulation
13. ❌ No scenario management
14. ❌ No multi-store correlation

---

## Detailed Component Audit

### 1. RetailSimulator.run() - Environment Loop
**File**: `src/simulation/environment.py`

| Aspect | Current | Status | Needed |
|--------|---------|--------|--------|
| **Demand source** | None (synthetic) | ❌ **PLACEHOLDER** | LightGBM/XGBoost forecast per store |
| **Inventory depletion** | None (ignored) | ❌ **PLACEHOLDER** | Daily: inventory -= demand |
| **Revenue calculation** | `revenue += 1000 + day * 10` | ❌ **HARDCODED** | `(demand_met * price) + partial_fulfillment_revenue` |
| **Profit calculation** | `profit += 150 + day * 2` | ❌ **HARDCODED** | `revenue - (inventory_cost + stockout_cost + waste_cost)` |
| **Fill rate** | Constant 0.95 | ❌ **HARDCODED** | `demand_met / (demand_met + lost_sales)` |
| **Stockout simulation** | None | ❌ **MISSING** | Track unmet demand; apply service level penalty |
| **Supplier integration** | Entities exist, never called | ❌ **UNUSED** | Process shipments, track lead time variance |
| **Inventory aging** | None | ❌ **MISSING** | Depreciation based on shelf_life_days |

**Replacement Strategy**:
```python
# NEEDED: Per-day simulation loop
for day in range(days):
    demand = forecast[store][day]  # From trained model
    available = store.inventory[product_id]
    demand_met = min(demand, available)
    lost_sales = max(0, demand - available)
    
    # Update inventory
    store.update_stock(product_id, -demand_met)
    
    # Calculate financials
    revenue += demand_met * product.base_price
    stockout_cost += lost_sales * product.base_price * stockout_penalty
    waste += inventory_depreciation(available, product.shelf_life_days)
```

---

### 2. Metrics Calculation
**File**: `src/simulation/environment.py`, lines 25-26

| Metric | Current | Status | Needed |
|--------|---------|--------|--------|
| **revenue** | `0.0 + 1000 + day*10` | ❌ **FAKE** | Sum of (demand_met * price) across all stores/products |
| **profit** | `0.0 + 150 + day*2` | ❌ **FAKE** | revenue - (cogs + stockout + waste + transport) |
| **fill_rate** | `0.95` (constant) | ❌ **FAKE** | (units_sold / total_demand) across all stores |
| **stockout_rate** | Never set | ❌ **MISSING** | (days_with_zero_inventory / total_days) per store |
| **on_time_delivery_rate** | Never set | ❌ **MISSING** | (shipments_on_time / total_shipments) |

**Replacement Strategy**:
- Track real metrics per day and per store
- Aggregate to account-level KPIs
- Store in `SimulationDailyMetrics` (new dataclass)

---

### 3. Demand Generation
**File**: Missing entirely

| Component | Current | Status | Needed |
|-----------|---------|--------|--------|
| **Forecast source** | None | ❌ **MISSING** | Load lgb_model_{store}.bin and generate day-by-day forecast |
| **External factor application** | Generated but unused | ❌ **UNUSED** | demand = forecast[day] * external_factors[day].demand_multiplier |
| **Customer variability** | None | ❌ **MISSING** | Add ±15% normal noise to demand |
| **Promotional impact** | None | ❌ **MISSING** | Simulate price elasticity (demand *= 0.8 at +20% price) |

**Replacement Strategy**:
```python
# NEEDED: DemandGenerator class
class DemandGenerator:
    def __init__(self, store_id, model_artifact, external_factors):
        self.store_id = store_id
        self.forecast = load_model_forecast(model_artifact)
        self.external_factors = external_factors
    
    def get_demand(self, day, price_delta=0.0):
        base_demand = self.forecast[day]
        external_multiplier = self.external_factors[day].demand_multiplier
        customer_noise = np.random.normal(1.0, 0.15)
        price_elasticity = 1.0 - (price_delta / 100.0) * 0.5  # 0.5 elasticity
        return base_demand * external_multiplier * customer_noise * price_elasticity
```

---

### 4. Inventory Management
**File**: `src/simulation/entities.py`, lines 36-40, 58-62

| Aspect | Current | Status | Needed |
|--------|---------|--------|--------|
| **Stock tracking** | Dict[product_id, qty] | ✅ Structure exists | Use real daily depletion |
| **Reorder logic** | None | ❌ **MISSING** | Reorder when inventory < reorder_point |
| **Lead time simulation** | Supplier.avg_lead_time_days defined | ❌ **UNUSED** | Add variance to lead time; track shipment dates |
| **Aging/spoilage** | None | ❌ **MISSING** | Depreciate based on shelf_life_days |
| **Capacity constraints** | Warehouse.can_accept() exists | ✅ Logic exists | Enforce in replenishment |
| **Safety stock calculation** | None | ❌ **MISSING** | safety_stock = z_score * σ(demand) * sqrt(lead_time) |

**Replacement Strategy**:
- Track `received_date` and `expiration_date` per inventory batch
- Daily check: if age >= shelf_life, remove and count as waste
- Implement reorder point policy: `reorder_qty = forecast[next_14_days].mean() * (1 + lead_time_variability)`

---

### 5. Supplier & Logistics
**File**: `src/simulation/entities.py`, lines 74-83

| Component | Current | Status | Needed |
|-----------|---------|--------|--------|
| **Supplier reliability** | Defined but unused | ❌ **UNUSED** | Apply 1-reliability_score as failure rate |
| **Lead time variance** | avg_lead_time_days only | ❌ **INCOMPLETE** | actual_lead_time = normal(avg, σ=avg*0.2) |
| **Shipment tracking** | Shipment dataclass exists | ✅ Structure exists | Emit RestockRequest → Shipment → Receipt events |
| **Transportation cost** | None | ❌ **MISSING** | cost = quantity * distance / mode_efficiency |
| **Supplier delays** | Not simulated | ❌ **MISSING** | Apply disruption events randomly per scenario |

**Replacement Strategy**:
```python
# NEEDED: Supply chain event loop
class SupplyChainSimulator:
    def process_restock_requests(self, day):
        for request in restock_queue:
            # Check supplier reliability
            if random() > supplier.reliability_score:
                emit(ShipmentDelayed(request, delay_days=5))
                continue
            
            # Generate actual lead time
            lead_time = int(np.random.normal(
                supplier.avg_lead_time_days,
                supplier.avg_lead_time_days * 0.2
            ))
            arrival_day = day + lead_time
            emit(ShipmentScheduled(request, arrival_day))
```

---

### 6. External Factors
**File**: `src/simulation/external_factors.py`

| Component | Current | Status | Needed |
|-----------|---------|--------|--------|
| **Holiday detection** | Hardcoded Dec 25, Jan 1 | ⚠️ **MINIMAL** | Include retail calendar: Easter, Black Friday, etc. |
| **Weather impact** | Constant 0.2 or 0.25 | ❌ **FAKE** | Use seasonal/regional data; affect transportation |
| **Demand multiplier** | 1.2 for holiday, +0.05 weekend | ⚠️ **SIMPLISTIC** | Store/category specific (e.g., dairy demand ↑ weekend vs clothing) |
| **Price optimization** | None | ❌ **MISSING** | Generate optimal_price based on demand elasticity |

**Replacement Strategy**:
```python
# ENHANCED ExternalFactors
@dataclass
class ExternalFactors:
    date: datetime
    is_holiday: bool
    holiday_type: str  # "christmas", "black_friday", "easter"
    is_weekend: bool
    is_promo_period: bool
    weather_condition: str  # "clear", "rain", "snow"
    temperature_anomaly: float  # °F deviation from seasonal normal
    demand_multiplier: Dict[str, float]  # Per category: {"grocery": 1.2, "apparel": 0.8}
    price_elasticity: float  # -1.5 for essentials, -3.0 for discretionary
```

---

### 7. API Integration
**File**: `src/api/routes/simulation.py`

| Endpoint | Current | Status | Needed |
|----------|---------|--------|--------|
| **POST /simulation/start** | Creates RetailSimulator, runs with hardcoded days | ⚠️ **PARTIAL** | Accept store_ids, product_ids, scenarios |
| **GET /simulation/metrics** | Returns hardcoded zeros | ❌ **FAKE** | Return actual metrics from simulation state |
| **POST /simulation/disrupt** | Queues disruption but doesn't apply | ❌ **UNUSED** | Inject: supplier_delay, demand_spike, inventory_loss |
| **GET /simulation/status** | Shows running flag only | ⚠️ **MINIMAL** | Add: current_day, events_queued, metrics_snapshot |

**Replacement Strategy**:
- Add `/simulation/start?stores=CA_1,CA_2&scenario=supplier_delay`
- Return real-time metrics in `/metrics` endpoint
- Implement disruption handler that modifies supplier reliability, demand multiplier, or inventory
- Add `/simulation/events` to stream real events

---

### 8. Dashboard Integration
**File**: `src/dashboard/pages/simulation_control.py`

| Component | Current | Status | Needed |
|-----------|---------|--------|--------|
| **Simulation history** | Placeholder _generate_history() | ❌ **FAKE** | Load from database or run state |
| **Progress tracking** | Placeholder _get_progress_data() | ❌ **FAKE** | Real day counter, scenario progress |
| **KPI visualization** | None | ❌ **MISSING** | Real-time revenue, profit, stockout rate |
| **Scenario results** | None | ❌ **MISSING** | Side-by-side comparison charts |
| **Store selector** | None | ❌ **MISSING** | Multi-select with per-store KPIs |

**Replacement Strategy**:
- Integrate with real simulation results
- Add scenario selector and execution UI
- Display live KPI dashboard: revenue, profit, fill_rate, stockout_rate
- Add store-level breakdown (heatmap of stockout rates)
- Comparison: baseline vs disruption scenarios

---

### 9. Event Emission
**File**: `src/simulation/environment.py`

| Event | Current | Status | Needed |
|-------|---------|--------|--------|
| **DemandForecastUpdated** | Defined in events.py but never emitted | ❌ **UNUSED** | Emit when forecast loaded per store |
| **RestockRequest** | Defined but never emitted | ❌ **UNUSED** | Emit when reorder_point triggered |
| **ShipmentScheduled** | Not defined | ❌ **MISSING** | New event: supplier → warehouse transit |
| **StockoutOccurred** | Not defined | ❌ **MISSING** | New event: demand > inventory |
| **InventoryExpired** | Not defined | ❌ **MISSING** | New event: age >= shelf_life |

**Replacement Strategy**:
- Implement `SimulationEventBus` to emit events during loop
- Store events in list for replay/analysis
- Provide `/simulation/events/{simulation_id}` endpoint

---

### 10. Multi-Store Correlation
**File**: Entire simulation layer

| Aspect | Current | Status | Needed |
|--------|---------|--------|--------|
| **Cross-store demand** | None | ❌ **MISSING** | Regional demand shocks affect multiple stores |
| **Warehouse replenishment** | Hardcoded per store | ❌ **MISSING** | Warehouse services multiple stores; optimize allocation |
| **Competitive pricing** | None | ❌ **MISSING** | Competitor actions affect demand |

**Replacement Strategy**:
- Add RegionalDemandFactor that applies to all CA stores simultaneously
- Implement warehouse-to-store allocation logic
- Optional: competitor pricing adjustments

---

### 11. Scenario Management
**File**: None exists

| Scenario | Status | Needed |
|----------|--------|--------|
| **Baseline** | ❌ Missing | Run with normal demand, no disruptions |
| **Supplier delay (+7 days)** | ❌ Missing | Increase lead_time for selected supplier |
| **Demand spike (+50%)** | ❌ Missing | Multiply external_factors.demand_multiplier * 1.5 for 7 days |
| **Inventory loss (30%)** | ❌ Missing | Reduce warehouse inventory by 30% on day 5 |
| **Price war (-20%)** | ❌ Missing | Reduce price by 20%; observe demand elasticity impact |

**Replacement Strategy**:
- Create `SimulationScenario` class with scenario name and parameter overrides
- Store results in `SimulationRun` dataclass
- Generate comparison report

---

### 12. KPI Calculations
**File**: None exists properly

| KPI | Formula Needed | Status |
|-----|---|--------|
| **Revenue** | SUM(demand_met[i] * price[i]) | ❌ Missing |
| **Profit** | revenue - cogs - stockout_cost - waste_cost - transport_cost | ❌ Missing |
| **Fill rate** | demand_met / (demand_met + lost_sales) | ❌ Missing |
| **Stockout rate** | days_with_zero_inv / total_days | ❌ Missing |
| **Inventory turnover** | cogs / avg_inventory | ❌ Missing |
| **Service level** | 1 - (total_lost_sales / total_demand) | ❌ Missing |
| **Waste %** | waste_units / total_demand | ❌ Missing |

**Replacement Strategy**:
```python
@dataclass
class SimulationDailyMetrics:
    day: int
    revenue: float  # Real calculation
    profit: float   # Real calculation
    demand: float
    demand_met: float
    lost_sales: float
    fill_rate: float
    stockouts: int
    waste: float
    inventory_level: float
    on_order: float

@dataclass
class SimulationRunMetrics:
    total_revenue: float
    total_profit: float
    avg_fill_rate: float
    stockout_rate: float  # % days with stockout
    inventory_turnover: float
    service_level: float
    waste_rate: float
```

---

### 13. Forecast Integration
**File**: None exists in simulation

| Requirement | Status | Needed |
|-------------|--------|--------|
| **Load LightGBM artifact** | ❌ Missing | Load `models/lgb_model_{store}.bin` per store |
| **Load XGBoost artifact** | ❌ Missing | Load `models/xgb_model_{store}.json` per store |
| **Generate per-day forecast** | ❌ Missing | Call model.predict(features) for each day |
| **Apply confidence intervals** | ❌ Missing | Use p10/p50/p90 from ensemble |
| **Demand sampling** | ❌ Missing | Sample from distribution: demand ~ N(p50, σ) |

**Replacement Strategy**:
```python
class ForecastIntegration:
    def __init__(self, store_id, model_type="lgbm"):
        self.model = load_model(f"models/{model_type}_model_{store_id}.bin")
    
    def generate_forecast(self, features_df, days=28):
        # Iterative forecast for each day
        forecasts = []
        for day in range(days):
            pred = self.model.predict(features_df[day:day+1])
            forecasts.append(pred[0])
        return forecasts
    
    def sample_demand(self, forecasted_p50, p10, p90):
        sigma = (p90 - p10) / 3.29  # 99.7% within range
        return np.random.normal(forecasted_p50, sigma)
```

---

### 14. Testing
**File**: `tests/integration/test_full_system.py` (currently minimal)

| Test Type | Current | Status | Needed |
|-----------|---------|--------|--------|
| **Unit: Demand generation** | None | ❌ Missing | Test DemandGenerator with known forecast |
| **Unit: Inventory depletion** | None | ❌ Missing | Test: 100 units - 30 demand = 70 remaining |
| **Unit: KPI calculation** | None | ❌ Missing | Test: revenue = 30 * $10.00 |
| **Integration: Forecast → Sim** | None | ❌ Missing | Test: Load real model, run day, verify demand >= 0 |
| **Integration: API → Sim** | None | ❌ Missing | Test: POST /start → GET /metrics returns real values |
| **E2E: Full scenario** | Exists but minimal | ⚠️ **INCOMPLETE** | Test: Load model → run sim → verify KPIs → check consistency |
| **E2E: Scenario comparison** | None | ❌ Missing | Test: baseline vs disruption scenario differ as expected |

**Replacement Strategy**:
- Add `tests/integration/test_simulation_realistic.py`
- Test demand generation, inventory tracking, KPI calculation
- Test forecast integration with real model artifacts

---

## Summary: Critical Path to Production

### Phase 4 Deliverables (In Order)

1. **Demand Generator** (use trained forecasts)
2. **Inventory Simulator** (real depletion, reorder logic)
3. **KPI Calculator** (revenue, profit, fill_rate, etc.)
4. **Supply Chain Simulator** (supplier delays, lead times)
5. **Scenario Manager** (baseline, disruptions)
6. **Event Emitter** (RestockRequest, Shipment, Stockout events)
7. **API Integration** (real metrics endpoints)
8. **Dashboard Integration** (live KPI visualization)
9. **Testing Suite** (unit, integration, E2E)
10. **Reports** (scenario comparison, KPI analysis)

### Completion Metrics

✅ All components must pass:
- `pytest` (16+ tests with real simulation tests)
- `compileall src` (no syntax errors)
- `pip check` (no broken dependencies)
- Manual test: Simulation runs with real forecasts, produces non-constant metrics
- API validation: `/simulation/metrics` returns dynamic values
- Dashboard: Live KPI display, scenario comparison

---

## Blockers & Dependencies

- ✅ Phase 3 prerequisite: All store LightGBM models trained
- ⏳ Needed: XGBoost models (for ensemble, Phase 4 step 2)
- ⏳ Needed: Prophet/Ensemble comparison (for optional multi-model sim)

