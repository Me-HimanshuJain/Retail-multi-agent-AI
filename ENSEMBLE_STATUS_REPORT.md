# ENSEMBLE_STATUS_REPORT


Summary of ensemble performance across stores and recommended next steps.


## Per-store metrics


| Store | LightGBM WRMSSE | XGBoost WRMSSE | Ensemble WRMSSE | Improvement % | Weights |
|---|---:|---:|---:|---:|---|
| CA_1.metrics | 103.30613501621171 | 150.76823612446515 | 48.98978468181583 | 52.58 | {'lgbm': 0.8704723437651298, 'xgb': 0.12952765623487028} |
| CA_2.metrics | 84.91521274782262 | 215.66798080511623 | 42.22975242214075 | 50.27 | {'lgbm': 0.9436696664910406, 'xgb': 0.05633033350895939} |
| CA_3.metrics | 111.45074092737234 | 115.72193064706909 | 57.58445997440291 | 48.33 | {'lgbm': 0.9607639286905041, 'xgb': 0.03923607130949594} |
| CA_4.metrics | 63.33416997430743 | 75.4675187881256 | 32.23431868992046 | 49.1 | {'lgbm': 0.9565066719914679, 'xgb': 0.04349332800853221} |
| TX_1.metrics | 63.629561137125485 | 133.83054669060886 | 33.99191192822335 | 46.58 | {'lgbm': 0.9746465383102191, 'xgb': 0.02535346168978085} |
| TX_2.metrics | 128.8420263194955 | 109.94683250614152 | 59.48378606769317 | 53.83 | {'lgbm': 0.7470311543534266, 'xgb': 0.2529688456465734} |
| TX_3.metrics | 60.11007373969684 | 115.2934772214661 | 32.79539864913076 | 45.44 | {'lgbm': 0.99, 'xgb': 0.01} |
| WI_1.metrics | 100.49564547800327 | 224.26541690842953 | 47.668184752122194 | 52.57 | {'lgbm': 0.9194297838464252, 'xgb': 0.08057021615357482} |
| WI_2.metrics | 235.83810466040362 | 211.30308760599584 | 100.25114868303274 | 57.49 | {'lgbm': 0.7248926998948546, 'xgb': 0.2751073001051454} |
| WI_3.metrics | 141.45643578203845 | 179.70392815084332 | 60.537676974838924 | 57.2 | {'lgbm': 0.8102780966658873, 'xgb': 0.18972190333411257} |


## Aggregate


- Average ensemble improvement vs LightGBM: 51.34%


## Limitations


- WRMSSE depends on correct hierarchical weights; ensure consistency with production evaluation.
- Ensembles currently combine only LightGBM and XGBoost; Prophet support is optional and can be added.
- Multi-step forecasting beyond single-point predictions requires sequence feature engineering (recursive or direct strategies).


## Recommended next steps


- Expose per-store ensemble weights in the dashboard and API endpoints.
- Add Prophet members to ensemble if validation shows complementary strengths.
- Add thorough integration tests for ensemble inference paths.
- Monitor model drift and schedule periodic retraining.