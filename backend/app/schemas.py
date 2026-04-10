from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LaunchRunRequest(BaseModel):
    preset_key: str | None = None
    display_name: str | None = None
    seed: int | None = None
    epochs: int | None = Field(default=None, ge=4, le=40)
    config: dict[str, Any] | None = None


class PresetSummary(BaseModel):
    key: str
    display_name: str
    description: str
    dataset_name: str
    task_type: str
    model_name: str
    config: dict[str, Any]


class RunSummary(BaseModel):
    run_id: str
    display_name: str
    preset_key: str
    dataset_name: str
    task_type: str
    model_name: str
    status: str
    seed: int
    latest_message: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    scorecard: dict[str, Any]


class RunListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[RunSummary]


class MetricPointResponse(BaseModel):
    step: int
    split: str
    loss: float | None = None
    accuracy: float | None = None
    f1: float | None = None
    auroc: float | None = None
    mae: float | None = None
    rmse: float | None = None
    r2: float | None = None
    created_at: datetime


class ArtifactResponse(BaseModel):
    name: str
    artifact_type: str
    mime_type: str
    relative_path: str
    download_url: str


class RunDetailResponse(BaseModel):
    run: RunSummary
    config: dict[str, Any]
    artifacts: list[ArtifactResponse]

