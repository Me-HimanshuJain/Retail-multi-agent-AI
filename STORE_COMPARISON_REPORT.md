# Store Comparison Report

## Scope

Trained LightGBM artifacts for 10 stores (CA_1 through WI_3) with M5 dataset.

## Metrics

- RMSE: root mean squared error
- MAE: mean absolute error  
- MAPE: mean absolute percentage error
- WRMSSE: weighted RMSE scaled by M5 hierarchy
- Training Duration: elapsed time in seconds

## Store Ranking (by average rank across metrics)

| Store Rank | Store ID | RMSE | MAE | MAPE | WRMSSE | Duration (s) | Overall Rank |
|---|---|---|---|---|---|---|---|
| 1 | TX_3 | 2.16 | 1.09 | 60.58 | 60.11 | 34.28 | 2.20 |
| 2 | TX_1 | 2.02 | 1.02 | 63.46 | 63.63 | 108.20 | 3.80 |
| 3 | WI_1 | 1.86 | 1.09 | 63.73 | 100.50 | 62.99 | 3.80 |
| 4 | CA_4 | 1.71 | 0.94 | 64.86 | 63.33 | 157.08 | 4.20 |
| 5 | CA_2 | 2.17 | 1.29 | 61.84 | 84.92 | 68.85 | 4.80 |
| 6 | CA_1 | 2.37 | 1.27 | 59.40 | 103.31 | 80.27 | 5.20 |
| 7 | TX_2 | 2.21 | 1.14 | 61.41 | 128.84 | 120.76 | 6.00 |
| 8 | WI_3 | 2.32 | 1.12 | 72.35 | 141.46 | 199.17 | 8.00 |
| 9 | CA_3 | 2.90 | 1.52 | 64.59 | 111.45 | 147.14 | 8.20 |
| 10 | WI_2 | 3.22 | 1.48 | 80.75 | 235.84 | 94.66 | 8.80 |

## Top Performer

**TX_3** with overall rank score 2.20

## Plot Artifacts

- RMSE comparison: `models/store_rmse_comparison.png`
- MAE comparison: `models/store_mae_comparison.png`
- MAPE comparison: `models/store_mape_comparison.png`
- WRMSSE comparison: `models/store_wrmsse_comparison.png`
- Training duration comparison: `models/store_training_time_sec_comparison.png`
