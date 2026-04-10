from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Run  # noqa: E402
from app.services.runner import RunOrchestrator  # noqa: E402
from app.schemas import LaunchRunRequest  # noqa: E402


def reset_storage() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    runs_root = settings.storage_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    for item in runs_root.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)


def main() -> None:
    reset_storage()
    orchestrator = RunOrchestrator(SessionLocal)
    for preset in ["customer-churn", "predictive-maintenance", "demand-forecasting"]:
        orchestrator.create_and_start_run(LaunchRunRequest(preset_key=preset))

    while True:
        with SessionLocal() as session:
            runs = session.query(Run).all()
            statuses = [run.status for run in runs]
        if runs and all(status in {"completed", "failed"} for status in statuses):
            break
        time.sleep(0.25)

    orchestrator.shutdown()
    print("Seeded demo runs.")


if __name__ == "__main__":
    main()

