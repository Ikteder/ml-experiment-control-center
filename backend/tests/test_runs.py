from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_list_presets(client: TestClient) -> None:
    response = client.get("/api/v1/presets")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert any(item["key"] == "predictive-maintenance" for item in payload)


def test_launch_run_and_fetch_detail(client: TestClient) -> None:
    launch_response = client.post("/api/v1/runs", json={"preset_key": "customer-churn", "epochs": 6})
    assert launch_response.status_code == 200
    run_id = launch_response.json()["run_id"]

    detail_response = client.get(f"/api/v1/runs/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["run"]["preset_key"] == "customer-churn"
    assert detail["config"]["epochs"] == 6


def test_runs_endpoint_supports_filters(client: TestClient) -> None:
    client.post("/api/v1/runs", json={"preset_key": "predictive-maintenance"})
    response = client.get("/api/v1/runs", params={"preset_key": "predictive-maintenance"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert all(item["preset_key"] == "predictive-maintenance" for item in payload["items"])

