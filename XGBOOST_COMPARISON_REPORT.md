# LightGBM vs XGBoost Comparison Report

## Scope

Comparative evaluation of LightGBM and XGBoost models trained on M5 dataset for 10 stores.

## Executive Summary

- **LightGBM wins**: 37 metrics (out of 40)
- **XGBoost wins**: 3 metrics (out of 40)
- **Average WRMSSE - LightGBM**: 109.34
- **Average WRMSSE - XGBoost**: 153.20
- **Best overall performer**: LightGBM

## Performance by Store

| Store | LightGBM WRMSSE | XGBoost WRMSSE | Delta | Winner |
|---|---|---|---|---|
| CA_1 | 103.31 | 150.77 | +47.46 | LightGBM |
| CA_2 | 84.92 | 215.67 | +130.75 | LightGBM |
| CA_3 | 111.45 | 115.72 | +4.27 | LightGBM |
| CA_4 | 63.33 | 75.47 | +12.13 | LightGBM |
| TX_1 | 63.63 | 133.83 | +70.20 | LightGBM |
| TX_2 | 128.84 | 109.95 | -18.90 | XGBoost |
| TX_3 | 60.11 | 115.29 | +55.18 | LightGBM |
| WI_1 | 100.50 | 224.27 | +123.77 | LightGBM |
| WI_2 | 235.84 | 211.30 | -24.54 | XGBoost |
| WI_3 | 141.46 | 179.70 | +38.25 | LightGBM |

## Metrics Comparison

### RMSE (Root Mean Squared Error) - Lower is Better
| Store | LightGBM | XGBoost | Winner |
|---|---|---|---|
| CA_1 | 2.37 | 2.82 | LightGBM |
| CA_2 | 2.17 | 3.00 | LightGBM |
| CA_3 | 2.90 | 3.56 | LightGBM |
| CA_4 | 1.71 | 1.86 | LightGBM |
| TX_1 | 2.02 | 2.22 | LightGBM |
| TX_2 | 2.21 | 2.46 | LightGBM |
| TX_3 | 2.16 | 2.55 | LightGBM |
| WI_1 | 1.86 | 2.25 | LightGBM |
| WI_2 | 3.22 | 3.78 | LightGBM |
| WI_3 | 2.32 | 2.79 | LightGBM |

### MAE (Mean Absolute Error) - Lower is Better
| Store | LightGBM | XGBoost | Winner |
|---|---|---|---|
| CA_1 | 1.27 | 1.40 | LightGBM |
| CA_2 | 1.29 | 1.41 | LightGBM |
| CA_3 | 1.52 | 1.79 | LightGBM |
| CA_4 | 0.94 | 0.99 | LightGBM |
| TX_1 | 1.02 | 1.05 | LightGBM |
| TX_2 | 1.14 | 1.22 | LightGBM |
| TX_3 | 1.09 | 1.22 | LightGBM |
| WI_1 | 1.09 | 1.19 | LightGBM |
| WI_2 | 1.48 | 1.50 | LightGBM |
| WI_3 | 1.12 | 1.19 | LightGBM |

### MAPE (Mean Absolute Percentage Error) - Lower is Better
| Store | LightGBM | XGBoost | Winner |
|---|---|---|---|
| CA_1 | 59.40 | 73.47 | LightGBM |
| CA_2 | 61.84 | 71.56 | LightGBM |
| CA_3 | 64.59 | 80.24 | LightGBM |
| CA_4 | 64.86 | 72.24 | LightGBM |
| TX_1 | 63.46 | 74.56 | LightGBM |
| TX_2 | 61.41 | 72.79 | LightGBM |
| TX_3 | 60.58 | 74.24 | LightGBM |
| WI_1 | 63.73 | 71.52 | LightGBM |
| WI_2 | 80.75 | 75.27 | XGBoost |
| WI_3 | 72.35 | 75.44 | LightGBM |

### WRMSSE (Weighted Root Mean Squared Scaled Error) - Lower is Better
| Store | LightGBM | XGBoost | Winner |
|---|---|---|---|
| CA_1 | 103.31 | 150.77 | LightGBM |
| CA_2 | 84.92 | 215.67 | LightGBM |
| CA_3 | 111.45 | 115.72 | LightGBM |
| CA_4 | 63.33 | 75.47 | LightGBM |
| TX_1 | 63.63 | 133.83 | LightGBM |
| TX_2 | 128.84 | 109.95 | XGBoost |
| TX_3 | 60.11 | 115.29 | LightGBM |
| WI_1 | 100.50 | 224.27 | LightGBM |
| WI_2 | 235.84 | 211.30 | XGBoost |
| WI_3 | 141.46 | 179.70 | LightGBM |

## Training Duration

- **Average LightGBM duration**: 107.34 seconds
- **Average XGBoost duration**: 13.33 seconds
- **Faster**: XGBoost

## Recommendation

### For Production Ensemble

Both models show competitive performance. **Recommendation**:

- Use **LightGBM** as primary model (lower avg WRMSSE)
- Include **XGBoost** in ensemble for diversity
- Ensemble can achieve better generalization through weighted combination

## Plot Artifacts

- RMSE comparison: `models/comparison_rmse_lgb_vs_xgb.png`
- MAE comparison: `models/comparison_mae_lgb_vs_xgb.png`
- MAPE comparison: `models/comparison_mape_lgb_vs_xgb.png`
- WRMSSE comparison: `models/comparison_wrmsse_lgb_vs_xgb.png`
