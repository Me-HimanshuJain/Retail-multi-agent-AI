# Ensemble Forecasting Comparison Report

## Scope

Comparison of weighted ensemble forecasting (LightGBM + XGBoost) against individual models on M5 dataset.

## Executive Summary

- **Number of stores**: 10
- **Average Ensemble WRMSSE**: 51.58
- **Average LightGBM WRMSSE**: 109.34
- **Average XGBoost WRMSSE**: 153.20
- **Stores with ensemble improvement**: 10 / 10
- **Average improvement**: 53.42 WRMSSE points
- **Average improvement %**: 50.05%

## Performance by Store

| Store | LightGBM WRMSSE | XGBoost WRMSSE | Ensemble WRMSSE | LightGBM Weight | XGBoost Weight | Improvement | Improvement % |
|---|---|---|---|---|---|---|---|
| CA_1 | 103.31 | 150.77 | 48.99 | 0.870 | 0.130 | +54.32 | +52.58% |
| CA_2 | 84.92 | 215.67 | 42.23 | 0.944 | 0.056 | +42.69 | +50.27% |
| CA_3 | 111.45 | 115.72 | 57.58 | 0.961 | 0.039 | +53.87 | +48.33% |
| CA_4 | 63.33 | 75.47 | 32.23 | 0.957 | 0.043 | +31.10 | +49.10% |
| TX_1 | 63.63 | 133.83 | 33.99 | 0.975 | 0.025 | +29.64 | +46.58% |
| TX_2 | 128.84 | 109.95 | 59.48 | 0.747 | 0.253 | +50.46 | +45.90% |
| TX_3 | 60.11 | 115.29 | 32.80 | 0.990 | 0.010 | +27.31 | +45.44% |
| WI_1 | 100.50 | 224.27 | 47.67 | 0.919 | 0.081 | +52.83 | +52.57% |
| WI_2 | 235.84 | 211.30 | 100.25 | 0.725 | 0.275 | +111.05 | +52.56% |
| WI_3 | 141.46 | 179.70 | 60.54 | 0.810 | 0.190 | +80.92 | +57.20% |

## Ensemble Insights

### Weight Distribution

- **Average LightGBM weight**: 0.890
- **Average XGBoost weight**: 0.110
- **Stores favoring LightGBM** (weight > 0.5): 10
- **Stores favoring XGBoost** (weight > 0.5): 0

### Performance Improvement

- **Stores with positive improvement**: 10 / 10 (100.0%)
- **Best improvement**: 111.05 WRMSSE points (WI_2)
- **Worst regression**: 27.31 WRMSSE points (TX_3)

## Recommendation

### For Production Deployment

? **Ensemble is recommended**: 10 / 10 stores benefit from ensemble approach

- **Ensemble provides**: Diversity in predictions, reduced overfitting risk, improved robustness
- **Per-store weights**: Dynamically optimized via WRMSSE validation metric
- **Model combination**: Weighted average of LightGBM and XGBoost predictions

## Plot Artifacts

- Comparison & Weights: `models/ensemble_comparison_analysis.png`
