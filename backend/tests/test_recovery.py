from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import Run
from app.services.runner import RunOrchestrator


def test_startup_recovery_marks_abandoned_runs_failed(tmp_path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'recovery.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with sessions() as session:
        session.add(
            Run(
                run_id="run-interrupted",
                display_name="Interrupted run",
                preset_key="customer-churn",
                dataset_name="Synthetic Customer Churn",
                task_type="classification",
                model_name="Gradient Boosting Classifier",
                status="running",
                seed=13,
                config_version="1.1.0",
                config_json="{}",
                git_commit_hash="test-revision",
                scorecard_json="{}",
            )
        )
        session.commit()

    runner = RunOrchestrator(sessions, storage_root=tmp_path / "storage", step_delay_seconds=0)
    assert runner.recover_interrupted_runs() == 1
    with sessions() as session:
        recovered = session.scalar(select(Run).where(Run.run_id == "run-interrupted"))
        assert recovered is not None
        assert recovered.status == "failed"
        assert "previous local worker" in (recovered.error_message or "")

    runner.shutdown()
    engine.dispose()
