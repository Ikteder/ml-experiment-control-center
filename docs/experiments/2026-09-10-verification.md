# Verification Record: 1.1 Upgrade

Date: 2026-09-10

## Environment

- Python 3.13 virtual environment
- Node and npm versions available in the local project environment
- Demo database and artifacts under ignored `.demo-runtime/`

## Checks and observations

| Check | Result | Evidence |
| --- | --- | --- |
| Backend tests | 9 passed | API lifecycle, artifacts, logs, report, filtering, config rejection, isolated storage, deterministic lags, chronological split, and startup recovery |
| Frontend tests | 3 passed | Run table interaction, JSON config upload and launch, invalid JSON feedback |
| Frontend lint | Passed | Previous effect-state and dependency findings removed |
| Frontend production build | Passed | Main bundle reduced from 547.56 kB to 207.14 kB through lazy chart loading and current patched tooling |
| Frontend dependency audit | Passed | Clean lockfile install reports zero known vulnerabilities |
| Demo generation | 3 completed runs | Generated in isolated `.demo-runtime/` without touching normal run storage |
| Visual review | Passed | Real 1800 by 1200 dashboard capture plus generated evaluation and artifact graphics |

## Demo results

| Run | Result |
| --- | --- |
| Customer Churn Baseline | F1 `0.7550`, precision `0.8571`, recall `0.6746`, AUROC `0.9354` |
| Predictive Maintenance Classifier | F1 `0.5860`, precision `0.8514`, recall `0.4468`, AUROC `0.9135` |
| Demand Forecasting Regressor | RMSE `22.0294` vs seasonal-naive `22.9211`, improvement `3.89%` |

## Open limitations

The local worker does not resume partial training, and the application has no authentication or multi-tenant isolation. Synthetic metrics validate the pipeline only.

## CI follow-up

The first public matrix run exposed an inconsistent lockfile and a Windows-only Rolldown binary listed as a direct development dependency. The manifest and lockfile were regenerated so npm can select the correct optional native package on each operating system. Patched transitive tooling removed all 13 audit findings. Backend jobs already passed on Python 3.12 and 3.13 before this correction.
