# Migration Plan

## Phase 1: Forecasting

Replace all baseline forecasting code with real M5-style pipelines. Implement actual feature engineering, time-based splits, artifact persistence, and model evaluation.

## Phase 2: Training Pipelines

Convert the notebook-driven workflow into reproducible scripts that build datasets, train models, save artifacts, and record metrics.

## Phase 3: Inference

Add deterministic loaders for trained artifacts and expose prediction APIs that return point forecasts plus confidence intervals.

## Phase 4: Simulation

Replace hardcoded simulation metrics with event-driven inventory, demand, customer, price, warehouse, and supply transitions.

## Phase 5: API Integration

Connect API routes to trained forecasting models and live simulation state instead of constant responses.

## Phase 6: Dashboard Integration

Switch dashboard pages to real forecast, inventory, and KPI endpoints and remove synthetic visualizations.

## Phase 7: Tests

Add integration tests for train → save → load → predict, API tests for live inference, and E2E tests covering fresh clone through dashboard and simulation startup.

## Phase 8: Deployment

Finalize Docker, Docker Compose, CI, and cloud deployment paths with reproducible model artifacts and operational checks.

## Forecasting Scope for Phase 1

- Use M5-format data: sales_train_evaluation.csv, calendar.csv, sell_prices.csv, and weights.csv.
- Build lag, rolling, and calendar features.
- Train LightGBM and XGBoost models with Optuna tuning and TimeSeriesSplit.
- Evaluate with RMSE, MAE, MAPE, and WRMSSE.
- Save model artifacts as .bin files under models/.
- Provide train.py, evaluate.py, and predict.py entry points.

## Exit Criteria

- No mean-baseline or constant-prediction forecasting code remains in the forecasting package.
- Training uses real data inputs and produces saved artifacts.
- Evaluation metrics are computed from model predictions, not hardcoded values.
- Phase 1 tests pass with real artifact load/save behavior.
