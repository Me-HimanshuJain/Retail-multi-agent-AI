# Training Report

## Scope

- Phase 2 real training for M5 artifacts.
- Store focus: `CA_1`.
- Primary completed model: LightGBM.

## Data Notes

- Training consumed M5 files from `data/`.
- `calendar.csv` in this workspace does not include `d`; training code now synthesizes ordered `d` labels when missing.
- Data loader supports fallback to `sales_test_validation.csv` when `sales_train_validation.csv` is unavailable.

## Executed Training Command

```bash
python -m src.models.forecasting.train_lgbm --data-dir data --store-id CA_1 --model-path models/lgb_model_CA_1.bin --metrics-path models/lgb_model_CA_1.metrics.json --optuna-trials 2 --validation-days 7
```

## Real Metrics (CA_1)

- `mape`: `59.40394773024526`
- `rmse`: `2.37205999463893`
- `mae`: `1.2685027876652593`
- `smape`: `131.3554461312115`
- `wape`: `81.70958832963007`
- `wrmsse`: `103.30613501621171`
- `training_time_sec`: `80.27199779998045`

## Generated Artifacts

- `models/lgb_model_CA_1.bin`
- `models/lgb_model_CA_1.metrics.json`
- `models/ca1_feature_importance.csv`
- `models/ca1_feature_importance.png`
- `models/ca1_forecast_horizon.csv`
- `models/ca1_forecast_horizon.png`

## Available Training Scripts

- `src/models/forecasting/train_lgbm.py`
- `src/models/forecasting/train_xgboost.py`
- `src/models/forecasting/train_ensemble.py`

## Remaining Work

1. Train and persist `CA_1` XGBoost artifact.
2. Train and persist `CA_1` ensemble artifact.
3. Expand real training coverage to additional stores.
