from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, engine
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    runs_root = settings.storage_root / "runs"
    if runs_root.exists():
        for item in runs_root.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
    with TestClient(app) as test_client:
        yield test_client
