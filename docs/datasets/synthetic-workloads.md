# Dataset Card: Bundled Synthetic Workloads

Last reviewed: 2026-09-10

## Purpose

These datasets are deterministic software fixtures for exercising experiment management, evaluation, logging, artifact generation, and the review interface. They are not evidence about real customers, industrial assets, or demand.

| Workload | Construction | Target | Split |
| --- | --- | --- | --- |
| Customer churn | scikit-learn `make_classification`, 2,200 rows, 18 anonymous numeric features | Binary churn label | Seeded stratified 76/24 holdout |
| Predictive maintenance | scikit-learn `make_classification`, 2,600 rows, 24 anonymous sensor-like features | Binary failure-risk label | Seeded stratified 78/22 holdout |
| Retail demand | Deterministic daily trend, weekly/monthly seasonality, promotions, price variation, and seeded noise | Daily synthetic demand | First 80 percent train, final 20 percent test |

## Source, version, and license

- Source: generated locally by repository code; no external download.
- Configuration version: `1.1.0`.
- Date accessed: not applicable because generation is local.
- License: MIT, matching the repository.
- Personal, proprietary, and scraped data: none.

## Leakage controls

- Classification rows are split before model fitting and stratified by label.
- Forecasting uses an ordered final-block holdout.
- Forecast target lags and rolling means are shifted so they contain no same-day or future target value.
- The forecasting baseline uses the demand value from seven days earlier.

## Quality concerns

- Anonymous generated features do not reproduce real measurement error, missingness, drift, or causal structure.
- Class balance and separability are chosen parameters and may make the tasks easier than real data.
- The daily demand process is a simplified simulation without stockouts, holidays, product hierarchy, or regime changes.
- No subgroup or cross-device evaluation is meaningful for these fixtures.

## Intended use

Use these fixtures to verify software behavior and demonstrate evaluation hygiene. Replace them with versioned, licensed, domain-relevant data before interpreting model quality.
