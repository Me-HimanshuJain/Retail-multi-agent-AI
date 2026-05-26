# Project Realization Audit

## Scope

This audit focuses on the parts of the repository that still contain mocked, synthetic, baseline, or hardcoded behavior and therefore block a deployable real AI system.

## Priority Findings

| Priority | File | Current implementation | Placeholder? | Real? | Replacement required | Difficulty | Dependencies | Risk |
|---|---|---|---|---|---|---|---|---|
| 1 | src/models/forecasting/xgboost_model.py | Mean-baseline forecaster with synthetic feature importance and JSON state save/load | Yes | No | Load trained XGBoost artifact, remove baseline math, expose trained predictions and intervals | Medium | LightGBM/XGBoost, training artifacts, feature engineering | High: forecasting output is not learned |
| 2 | src/models/forecasting/prophet_model.py | Mean-baseline time-series wrapper with synthetic quantiles | Yes | No | Real Prophet training/inference wrapper with fitted seasonal/trend model | Medium | prophet, serialized model artifacts, date preprocessing | High: time-series forecast quality is mocked |
| 3 | src/models/forecasting/training.py | `_generate_mock_data` creates synthetic incrementing samples | Yes | No | Real M5 data ingestion and feature pipeline with train/evaluate split | Medium | M5 CSVs, feature engineering, model training libs | High: training inputs are fake |
| 4 | src/models/forecasting/ensemble.py | Constant-output ensemble with zeroed evaluation | Yes | No | Weighted ensemble over LGBM/XGB/Prophet outputs | High | Base model artifacts, validation set, weight optimization | High: ensemble is not usable |
| 5 | src/dashboard/pages/kpi.py | Hardcoded KPI numbers and synthetic trend/category/agent data | Yes | No | Load KPI metrics from simulation DB/API or computed results store | Medium | Simulation metrics backend, API or DB connector | Medium: dashboard misrepresents system health |
| 6 | src/dashboard/pages/forecast.py | Synthetic forecast curves and model comparison values | Yes | No | Query real forecast API and plot actual intervals/metrics | Medium | Forecast API, model outputs, confidence intervals | Medium |
| 7 | src/simulation/environment.py | Hardcoded revenue/profit increments and constant fill rate | Yes | No | Event-driven inventory/demand/supply simulation | High | Forecasts, inventory rules, stochastic distributions | High: simulation KPIs are fake |
| 8 | src/api/routes/simulation.py | Returns zeroed metrics regardless of simulation state | Yes | No | Return live simulation metrics and state transitions | Medium | Real simulator state, async task wiring | High |
| 9 | Training_result/ML_model_training_notebook.ipynb | Contains sample training workflow and export snippets; notebook not executed | Partial | Partial | Convert notebook into reproducible scripts or keep as reference only | Medium | Data files, model libs, execution environment | Medium |
| 10 | README.md | Still documents screenshot placeholders | Partial | No | Update with real screenshots and deployment instructions | Low | Final UI artifacts | Low |

## Search Results Summary

The repository still contains the following classes of non-real behavior:

- placeholder
- synthetic
- mock
- TODO
- baseline
- constant returns
- mean predictors
- hardcoded metrics
- fake simulation behavior

The search also surfaced a stale notebook export marker in [Training_result/ML_model_training_notebook.ipynb](Training_result/ML_model_training_notebook.ipynb) and several documentation-only placeholders in README and release checklists.

## Realization Status

| Layer | Status | Notes |
|---|---|---|
| API | Mostly real | Auth, health, and simulation routes exist and tests pass |
| Dashboard | Mostly real UI, but some metrics are synthetic | KPI and forecast pages still hardcode values |
| Forecasting | Not real yet | Baseline wrappers and mock data remain |
| Simulation | Not real yet | Deterministic KPI increments remain |
| Tests | Passing | Current tests pass, but they validate the mocked layer too |
| Deployment | Partially complete | Docker/CI/docs exist, but model realism is missing |

## Replacement Order

1. Forecasting models and training pipeline
2. Ensemble aggregation over real model outputs
3. Simulation state engine and KPI derivation
4. API wiring to live model and simulation outputs
5. Dashboard wiring to real APIs/metrics
6. Integration and end-to-end tests around training/inference/deployment
