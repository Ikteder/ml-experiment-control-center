from __future__ import annotations

import csv
import io
import time
from pathlib import Path

from fastapi.testclient import TestClient


def wait_for_terminal(client: TestClient, run_id: str, timeout_seconds: float = 10) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runs/{run_id}")
        assert response.status_code == 200
        detail = response.json()
        if detail["run"]["status"] in {"completed", "failed"}:
            return detail
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} did not finish within {timeout_seconds} seconds")


def test_list_presets(client: TestClient) -> None:
    response = client.get("/api/v1/presets")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    forecast = next(item for item in payload if item["key"] == "demand-forecasting")
    assert "Chronological" in forecast["description"]
    assert forecast["config"]["config_version"] == "1.1.0"


def test_classification_run_completes_with_evidence(client: TestClient) -> None:
    launch_response = client.post("/api/v1/runs", json={"preset_key": "customer-churn", "epochs": 6})
    assert launch_response.status_code == 200
    run_id = launch_response.json()["run_id"]
    detail = wait_for_terminal(client, run_id)

    assert detail["run"]["status"] == "completed"
    assert detail["config"]["epochs"] == 6
    assert 0 <= detail["run"]["scorecard"]["precision"] <= 1
    assert 0 <= detail["run"]["scorecard"]["recall"] <= 1
    artifact_names = {item["name"] for item in detail["artifacts"]}
    assert {"dataset_card.md", "model_card.md", "report.html", "confusion_matrix.png"} <= artifact_names

    metrics_response = client.get(f"/api/v1/runs/{run_id}/metrics")
    assert metrics_response.status_code == 200
    assert len(metrics_response.json()) == 6

    report_response = client.get(f"/api/v1/runs/{run_id}/report")
    assert report_response.status_code == 200
    assert run_id in report_response.text

    logs_response = client.get(f"/api/v1/runs/{run_id}/logs")
    assert logs_response.status_code == 200
    assert "Completed epoch 6" in logs_response.text


def test_forecast_uses_chronological_holdout_and_baseline(client: TestClient) -> None:
    launch_response = client.post("/api/v1/runs", json={"preset_key": "demand-forecasting"})
    assert launch_response.status_code == 200
    run_id = launch_response.json()["run_id"]
    detail = wait_for_terminal(client, run_id)

    scorecard = detail["run"]["scorecard"]
    assert detail["run"]["status"] == "completed"
    assert scorecard["seasonal_naive_rmse"] > 0
    assert scorecard["rmse"] > 0
    assert "rmse_improvement_pct" in scorecard

    predictions_response = client.get(f"/api/v1/runs/{run_id}/artifacts/predictions.csv")
    assert predictions_response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(predictions_response.text)))
    dates = [row["date"] for row in rows]
    assert dates == sorted(dates)
    assert all(row["seasonal_naive"] for row in rows)

    card_response = client.get(f"/api/v1/runs/{run_id}/artifacts/dataset_card.md")
    assert card_response.status_code == 200
    assert "chronological test window" in card_response.text
    assert "No external, personal, proprietary, or scraped data" in card_response.text


def test_runs_endpoint_supports_filters_and_pagination(client: TestClient) -> None:
    first = client.post("/api/v1/runs", json={"preset_key": "customer-churn", "display_name": "Alpha review"})
    second = client.post("/api/v1/runs", json={"preset_key": "predictive-maintenance", "display_name": "Beta review"})
    assert first.status_code == second.status_code == 200

    wait_for_terminal(client, first.json()["run_id"])
    wait_for_terminal(client, second.json()["run_id"])

    response = client.get("/api/v1/runs", params={"search": "alpha", "limit": 1, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["display_name"] == "Alpha review"


def test_invalid_config_is_rejected_before_queueing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs",
        json={"preset_key": "demand-forecasting", "config": {"samples": 20, "future_target": True}},
    )
    assert response.status_code == 400
    assert "Unsupported config field" in response.json()["detail"]


def test_test_client_uses_temporary_storage(client: TestClient, tmp_path: Path) -> None:
    storage_root = client.app.state.storage_root
    assert storage_root.is_relative_to(tmp_path)
