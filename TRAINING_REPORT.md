# Training Report

## Scope

- Phase 2 training bootstrap for real M5 artifacts.
- Store focus: `CA_1` first.

## Data Requirements

Place the following files under `data/`:

- `data/calendar.csv`
- `data/sell_prices.csv`
- `data/sales_train_validation.csv`
- `data/weights_validation.csv`

## Training Scripts

- `src/models/forecasting/train_lgbm.py`
- `src/models/forecasting/train_xgboost.py`
- `src/models/forecasting/train_ensemble.py`

## Current Artifacts

The repository now serves trained artifacts from `models/`.

- `models/lgb_model_CA_1.bin`
- `models/lgb_model_CA_2.bin`
- `models/lgb_model_CA_3.bin`
- `models/lgb_model_CA_4.bin`
- `models/lgb_model_TX_1.bin`
- `models/lgb_model_TX_2.bin`
- `models/lgb_model_TX_3.bin`
- `models/lgb_model_WI_1.bin`
- `models/lgb_model_WI_2.bin`
- `models/lgb_model_WI_3.bin`

## Metrics Collection

Each training script writes metrics JSON including:

- RMSE
- MAE
- MAPE
- WRMSSE
- Training time (seconds)

Run examples:

```bash
python -m src.models.forecasting.train_lgbm --data-dir data --store-id CA_1
python -m src.models.forecasting.train_xgboost --data-dir data --store-id CA_1
python -m src.models.forecasting.train_ensemble --data-dir data --store-id CA_1
```

## Feature Importance

- LightGBM importance is available from trained booster (`feature_importance`).
- XGBoost importance is available from `XGBoostForecaster.get_feature_importance()`.

## Plots

Use dashboard Forecast page for:

- point prediction
- confidence interval (`P10`, `P90`)
- model comparison table

## Notes

- This report intentionally avoids fabricated numbers.
- Metrics are generated only when training is run against real M5 data files.

## Current Run Status (This Workspace)

- Attempted real `CA_1` training with:

```bash
python -m src.models.forecasting.train_lgbm --data-dir data --store-id CA_1
```

- Result: failed fast with `FileNotFoundError: data/calendar.csv`.
- Interpretation: the phase-2 training code is wired and runnable, but the required raw M5 dataset files are not present in this workspace yet.
- No fabricated training metrics were produced.
