# Decision: Use Chronological Forecast Evaluation

Date: 2026-09-10  
Status: accepted

## Context

The demand workload was labeled as forecasting but used a random train/test split. Random splitting allows future dates to appear in training while earlier dates appear in evaluation. That does not represent a real forecasting decision and can produce an optimistic result.

## Decision

- Generate an explicit daily time index.
- Construct calendar, promotion, price, lag-1, lag-7, and shifted seven-day rolling-mean features.
- Ensure every lagged or rolling target feature uses only earlier dates.
- Train on the first 80 percent of usable rows and evaluate on the final 20 percent.
- Compare gradient boosting with a lag-7 seasonal-naive forecast.
- Report model and baseline MAE/RMSE, R2, date boundaries, and percentage RMSE improvement.

## Consequences

The result is harder to overstate and closer to a real offline forecast evaluation. The current model improves RMSE by only 3.9 percent over the baseline, which is modest but honest. A future version should add rolling-origin validation and prediction intervals before making stronger forecasting claims.
