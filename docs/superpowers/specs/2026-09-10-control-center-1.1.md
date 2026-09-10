# ML Experiment Control Center 1.1 Spec

Status: approved for implementation on 2026-09-10.

## Objective

Turn the existing portfolio prototype into a reproducible, employer-facing ML platform demonstration with safe tests, continuous integration, more defensible forecasting evaluation, durable run evidence, and README visuals taken from the real application.

## Scope

### Verification and safety

- Isolate every backend test in a temporary SQLite database and temporary artifact directory.
- Never delete or rewrite the project's shared demo storage from the test suite.
- Exercise completed runs, metrics, logs, reports, artifacts, filtering, and validation.
- Fix all frontend lint findings and expand interaction coverage.
- Add GitHub Actions for backend and frontend verification.

### ML evaluation

- Replace the forecasting-like random regression split with a chronological synthetic demand series.
- Build lag and calendar features using only current or earlier information.
- Hold out the final time block and compare the model with a seasonal-naive baseline.
- Report model and baseline MAE/RMSE, improvement percentages, and time boundaries.
- Add classification precision, recall, threshold, and confusion counts.
- Generate a dataset card and a richer model card for every run.

### Runtime and reproducibility

- Inject storage location and step delay into the run orchestrator so verification is isolated.
- Recover runs left in queued or running states after an interrupted local process.
- Accept an explicit source revision when `.git` is unavailable, including containers.
- Constrain configured CORS origins.
- Pin direct Python dependencies and use deterministic container installation commands.

### Portfolio presentation

- Put a real dashboard screenshot near the top of the README.
- Replace the mixed F1 and inverse-RMSE bar chart with separate, honestly labeled task evidence.
- Include a workflow screenshot or animation showing launch, tracking, comparison, and artifact review.
- Keep all visual claims tied to generated synthetic demo runs.

## Non-goals

- Hosted multi-user authentication or authorization
- A distributed job queue
- Production-scale model registry semantics
- Claims that synthetic workload performance transfers to real customer, maintenance, or demand data

## Acceptance criteria

- Backend tests use only temporary state and pass without deleting shared runs.
- Frontend lint, tests, and production build pass.
- Public CI passes for the committed source.
- The demand workload uses a chronological holdout and exposes a seasonal-naive comparison.
- Generated reports contain dataset and model cards with limitations.
- README visuals render from repository-relative paths and include descriptive alt text.
- README contains no em dash characters.
- Local and public `main` revisions match after publication.
