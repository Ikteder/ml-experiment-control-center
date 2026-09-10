from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEMO_ROOT = PROJECT_ROOT / ".demo-runtime"
DEMO_DATABASE = DEMO_ROOT / "app.db"
DEMO_STORAGE = DEMO_ROOT / "storage"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base  # noqa: E402
from app.models import Run  # noqa: E402
from app.schemas import LaunchRunRequest  # noqa: E402
from app.services.runner import RunOrchestrator  # noqa: E402


def reset_demo_runtime(engine) -> None:
    """Reset only the repository's disposable demo sandbox."""
    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    if DEMO_ROOT.resolve() not in DEMO_STORAGE.resolve().parents:
        raise RuntimeError("Refusing to reset storage outside .demo-runtime")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    runs_root = DEMO_STORAGE / "runs"
    if runs_root.exists():
        shutil.rmtree(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)


def main() -> None:
    engine = create_engine(
        f"sqlite:///{DEMO_DATABASE.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    reset_demo_runtime(engine)
    orchestrator = RunOrchestrator(sessions, storage_root=DEMO_STORAGE, step_delay_seconds=0)
    for preset in ["customer-churn", "predictive-maintenance", "demand-forecasting"]:
        orchestrator.create_and_start_run(LaunchRunRequest(preset_key=preset))

    while True:
        with sessions() as session:
            runs = session.query(Run).all()
            statuses = [run.status for run in runs]
        if runs and all(status in {"completed", "failed"} for status in statuses):
            break
        time.sleep(0.1)

    orchestrator.shutdown()
    engine.dispose()
    print(f"Seeded {len(runs)} demo runs in {DEMO_ROOT}.")


if __name__ == "__main__":
    main()
