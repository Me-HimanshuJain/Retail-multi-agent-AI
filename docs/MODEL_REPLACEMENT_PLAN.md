# Model Replacement Roadmap

This document lists discovered placeholder models / synthetic outputs in the repository, describes the current implementation, and proposes concrete replacement paths (dataset, training pipeline, saved artifact formats) ordered by estimated effort from fastest upgrade → hardest.

---

1) src/models/forecasting/xgboost_model.py

Current implementation
- Returns a constant "baseline" prediction: median = np.full(len(X), self.baseline). Feature importance is synthetic (linspace).

Replacement path
- Implement a real XGBoost regression pipeline using xgboost.XGBRegressor (or scikit-learn wrapper). Move training code into a trainer module: src/models/forecasting/xgboost_trainer.py and leave a thin runtime wrapper in xgboost_model.py that loads a saved artifact.

Expected dataset
- Historical sales table with columns: ds (datetime), y (float sales), product_id (int), store_id (int), plus optional covariates (price, promo flags, holiday, weather). Training input X: lag features produced by prepare_xgboost_data (already present in src/models/forecasting/training.py).

Expected training pipeline
- Data ingestion (CSV/DB) → filtering by product/store → feature engineering (lags, rolling statistics, calendar/holiday features, exogenous) → train/validation split (time-series CV) → hyperparameter tuning (Optuna or GridSearchCV) → train final model → evaluation and calibration → export model & metadata.

Saved artifact
- .pkl (joblib) or XGBoost native JSON/booster file. Acceptable: .pkl (easy), .json (xgboost native). (.pt or .ckpt only if moving to PyTorch; not necessary here).

Difficulty: Easy

---

2) src/models/forecasting/prophet_model.py

Current implementation
- Predicts a constant series equal to the historical mean (self.baseline). predict_quantiles uses ±10% around baseline.

Replacement path
- Replace the thin wrapper with a real Prophet/NeuralProphet/ARIMA wrapper. Implement training in a trainer module (src/models/forecasting/prophet_trainer.py) and keep a loader/saver for runtime use.

Expected dataset
- Time-series of ds (datetime), y (target) per product/store. Optional regressors: promotions, price, events.

Expected training pipeline
- Ingest and prepare series with prepare_prophet_data (exists) → fit Prophet model with regressors if available → cross-validate with historical folds → save model and changelog (serializer via joblib/pickle or model.to_json where supported) → expose predict/predictive intervals.

Saved artifact
- .pkl / joblib for the fitted Prophet model (or .json if the chosen library supports it). .pkl recommended for simplicity.

Difficulty: Easy

---

3) src/dashboard/pages/kpi.py

Current implementation
- Returns synthetic KPI numbers from _load_kpi_metrics (hard-coded scalars). Several helper generators create synthetic trend/category/agent dataframes.

Replacement path
- Replace with connectors that read aggregated KPIs from either: (A) the live simulation (RetailSimulator.get_metrics), or (B) a metrics database (Postgres, TimescaleDB) populated by the pipeline. Keep the helper UI code but load real metrics via a small service layer (src/dashboard/data/metrics.py).

Expected dataset
- Aggregated metrics table: date, revenue, profit, fill_rate, stockout_rate, on_time_delivery_rate, and optionally product/store breakdowns.

Expected pipeline
- ETL task to aggregate raw events → store into metrics table or expose an API endpoint → dashboard reads the endpoint or DB directly and visualizes metrics.

Saved artifact
- Not a model artifact; configuration/queries stored as SQL or small YAML. If KPIs are produced by ML models, those models follow the same artifact formats (.pkl/.pt).

Difficulty: Easy

---

4) src/models/forecasting/ensemble.py

Current implementation
- Returns simple constant baselines (0.0) or a synthetic baseline proportional to number of models. evaluate_all returns zeros. get_model_status marks models as ready.

Replacement path
- Implement a real ensemble orchestrator: load individual model artifacts and compute forecasts per model, then combine via simple averaging, weighted averaging (weights learned on historical validation set), or stacking. Add a training step for ensemble weights and a standardized interface for member models.

Expected dataset
- Per-model historical forecasts and actuals by time/product/store to learn weights and evaluate. Same base historical sales data used by base models.

Expected training pipeline
- For each base model: generate out-of-fold forecasts on training period → collect meta-features (per-model forecasts) → train meta-learner (linear regression or small XGBoost) for stacking/weights → persist ensemble weights or meta-learner artifact.

Saved artifact
- .pkl for ensemble metadata/weights or a small model file (.pkl/.joblib). If meta-learner is a deep model, .pt or .ckpt may be used.

Difficulty: Medium

---

5) src/models/forecasting/training.py (_generate_mock_data)

Current implementation
- _generate_mock_data returns a synthetic DataFrame with a naive incrementing pattern (100 + index % 10) used in examples and tests.

Replacement path
- Provide a realistic sample data loader producing representative historical data, or add a seed data script that pulls a sanitized sample from production or a recorded dataset (CSV/Parquet). Keep a small synthetic generator only for unit tests with clearly named test fixtures.

Expected dataset
- Historical sales dataset with ds, y, product_id, store_id and covariates. A small, committable example CSV/Parquet in data/samples/ for local development is recommended.

Expected training pipeline
- Replace in-memory mock generator usage with read_csv/read_parquet routines. Add test fixtures that supply small, deterministic sample files in tests/fixtures.

Saved artifact
- N/A (data files). If publishing example models trained on sample data, save artifacts as .pkl in models/artifacts/.

Difficulty: Medium

---

6) src/simulation/environment.py

Current implementation
- Simulated metrics are incremented by fixed amounts per day and constant fill_rate is set; the simulator uses placeholder logic for revenue, profit, and rates.

Replacement path
- Replace heuristic increments with event-driven simulation that consumes demand forecasts, applies inventory policies, simulates supplier lead times and fulfillment, and derives KPIs. Integrate DemandForecastUpdated events and real model outputs into the simulation loop.

Expected dataset
- Demand distributions, lead-time distributions, product/store catalogs, historical arrivals and stockouts for calibration.

Expected training pipeline
- Not a conventional model training pipeline; instead: calibrate stochastic components (demand distribution models, lead-time models) from historical data; optionally train demand models used as inputs (XGBoost/Prophet). Implement a validation harness to ensure simulated KPIs match historical distributions.

Saved artifact
- If demand models are used inside the simulator, save them as .pkl/.json/.pt depending on implementation.

Difficulty: Hard

---

Notes / Prioritization rationale
- Fastest wins: start by replacing runtime placeholders with model-loading wrappers that expect a saved artifact. The small training functions in src/models/forecasting/training.py already provide data preparation utilities which makes replacing the XGBoost baseline the fastest practical win. Prophet is similarly quick because data prep is already present. Ensembles and simulation require more design and calibration effort — do these after base models are in place.

Suggested quick wins (order)
1. Implement XGBoost trainer and save .pkl artifacts (Easy, high ROI)
2. Implement Prophet trainer and save artifacts (Easy)
3. Replace dashboard hard-coded KPIs to read simulation/metrics endpoint (Easy)
4. Implement ensemble orchestration & weight training (Medium)
5. Replace mock data generator with a small sample dataset and update tests to use fixtures (Medium)
6. Rework RetailSimulator to consume real forecasts and stochastic models (Hard)

Appendix: artifact format recommendations
- .pkl / joblib — general-purpose (scikit-learn, XGBoost wrappers, Prophet wrappers). Good default.
- .json / xgboost native — use when portability to XGBoost native API is desired.
- .pt — when training PyTorch models (LSTM/transformer demand models).
- .ckpt — TensorFlow/Keras checkpoints if using those frameworks.

---

If you want, I can: (1) implement the XGBoost trainer and save/load hooks, (2) implement Prophet trainer wrappers, or (3) wire the dashboard to read metrics from the simulator. Tell me which step to execute first and I'll implement it and add tests.
