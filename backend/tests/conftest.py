from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_path = tmp_path / "test.db"
    storage_root = tmp_path / "storage"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    test_app = create_app(
        database_engine=test_engine,
        session_factory=test_sessions,
        storage_root=storage_root,
        step_delay_seconds=0,
    )
    with TestClient(test_app) as test_client:
        yield test_client
    test_engine.dispose()
