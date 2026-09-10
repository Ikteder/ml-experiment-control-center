# Model Evaluation Summary

Run date: 2026-09-10  
Config version: `1.1.0`  
Data: bundled synthetic fixtures

## Results

| Workload | Primary metrics | Diagnostic interpretation |
| --- | --- | --- |
| Customer Churn Baseline | F1 `0.7550`, precision `0.8571`, recall `0.6746`, AUROC `0.9354` | Strong synthetic ranking, with 55 false negatives at threshold 0.5. |
| Predictive Maintenance Classifier | F1 `0.5860`, precision `0.8514`, recall `0.4468`, AUROC `0.9135` | High precision but misses more than half of positive cases. Accuracy alone would hide this. |
| Demand Forecasting Regressor | MAE `17.7950`, RMSE `22.0294`, R2 `0.2449` | Beats lag-7 seasonal naive RMSE `22.9211` by `3.89%`, a modest improvement. |

## Evaluation protocols

- Classification: one seeded stratified random holdout per preset, threshold 0.5.
- Forecasting: one chronological final-block holdout after constructing leakage-safe lag features.
- Forecast baseline: lag-7 seasonal naive.

## Intended use and non-goals

The estimators demonstrate the experiment-control workflow and artifact contract. They are not deployable churn, maintenance, or demand models. No business, safety, maintenance, or inventory decision should be made from these results.

## Risks and next evaluation work

- Add repeated or nested validation for classification variability.
- Tune thresholds against explicit false-positive and false-negative costs.
- Add rolling-origin forecast validation and prediction intervals.
- Test on unseen entities, devices, sessions, or environments when a real dataset is introduced.
- Record dataset and code versions from an immutable external registry for production use.
