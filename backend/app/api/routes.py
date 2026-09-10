from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..models import ArtifactEntry, MetricPoint, Run
from ..schemas import (
    ArtifactResponse,
    LaunchRunRequest,
    MetricPointResponse,
    PresetSummary,
    RunDetailResponse,
    RunListResponse,
    RunSummary,
)
from ..services.runner import RunOrchestrator


router = APIRouter()


def get_runner(request: Request) -> RunOrchestrator:
    return request.app.state.runner


def _scorecard(run: Run) -> dict:
    return json.loads(run.scorecard_json or "{}")


def _to_run_summary(run: Run) -> RunSummary:
    return RunSummary(
        run_id=run.run_id,
        display_name=run.display_name,
        preset_key=run.preset_key,
        dataset_name=run.dataset_name,
        task_type=run.task_type,
        model_name=run.model_name,
        status=run.status,
        seed=run.seed,
        latest_message=run.latest_message,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        scorecard=_scorecard(run),
    )


def _to_artifact_response(artifact: ArtifactEntry) -> ArtifactResponse:
    return ArtifactResponse(
        name=artifact.name,
        artifact_type=artifact.artifact_type,
        mime_type=artifact.mime_type,
        relative_path=artifact.relative_path,
        download_url=f"{settings.api_prefix}/runs/{artifact.run_id}/artifacts/{artifact.name}",
    )


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/presets", response_model=list[PresetSummary])
def list_presets(runner: RunOrchestrator = Depends(get_runner)) -> list[PresetSummary]:
    return [PresetSummary(**preset) for preset in runner.preset_summaries()]


@router.post("/runs", response_model=RunSummary)
def launch_run(
    payload: LaunchRunRequest,
    runner: RunOrchestrator = Depends(get_runner),
) -> RunSummary:
    try:
        run = runner.create_and_start_run(payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_run_summary(run)


@router.get("/runs", response_model=RunListResponse)
def list_runs(
    limit: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
    preset_key: str | None = None,
    status: str | None = None,
    dataset_name: str | None = None,
    db: Session = Depends(get_db),
    runner: RunOrchestrator = Depends(get_runner),
) -> RunListResponse:
    items, total = runner.list_runs(
        db,
        limit=limit,
        offset=offset,
        search=search,
        preset_key=preset_key,
        status=status,
        dataset_name=dataset_name,
    )
    return RunListResponse(total=total, limit=limit, offset=offset, items=[_to_run_summary(item) for item in items])


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str, db: Session = Depends(get_db), runner: RunOrchestrator = Depends(get_runner)) -> RunDetailResponse:
    try:
        run = runner.get_run(db, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    artifacts = runner.get_artifacts(db, run_id)
    return RunDetailResponse(
        run=_to_run_summary(run),
        config=json.loads(run.config_json),
        artifacts=[_to_artifact_response(artifact) for artifact in artifacts],
    )


@router.get("/runs/{run_id}/metrics", response_model=list[MetricPointResponse])
def get_metrics(
    run_id: str,
    db: Session = Depends(get_db),
    runner: RunOrchestrator = Depends(get_runner),
) -> list[MetricPointResponse]:
    try:
        runner.get_run(db, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rows = runner.get_metric_points(db, run_id)
    return [MetricPointResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(
    run_id: str,
    db: Session = Depends(get_db),
    runner: RunOrchestrator = Depends(get_runner),
) -> list[ArtifactResponse]:
    try:
        runner.get_run(db, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    artifacts = runner.get_artifacts(db, run_id)
    return [_to_artifact_response(artifact) for artifact in artifacts]


@router.get("/runs/{run_id}/artifacts/{artifact_name}")
def download_artifact(
    run_id: str,
    artifact_name: str,
    request: Request,
    db: Session = Depends(get_db),
    runner: RunOrchestrator = Depends(get_runner),
) -> FileResponse:
    artifacts = runner.get_artifacts(db, run_id)
    artifact = next((item for item in artifacts if item.name == artifact_name), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_name}' was not found.")
    absolute_path = request.app.state.storage_root / artifact.relative_path
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing from disk.")
    return FileResponse(path=absolute_path, media_type=artifact.mime_type, filename=artifact.name)


@router.get("/runs/{run_id}/logs")
async def stream_logs(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    runner: RunOrchestrator = Depends(get_runner),
) -> StreamingResponse:
    try:
        runner.get_run(db, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_stream() -> bytes:
        cursor = 0
        while True:
            lines, cursor = runner.read_logs(run_id, cursor)
            for line in lines:
                yield f"data: {json.dumps(line)}\n\n".encode("utf-8")
            if await request.is_disconnected():
                break
            if runner.is_terminal(run_id) and not lines:
                break
            await asyncio.sleep(settings.log_poll_interval_seconds)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs/{run_id}/report", response_class=HTMLResponse)
def export_report(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    runner: RunOrchestrator = Depends(get_runner),
) -> HTMLResponse:
    artifacts = runner.get_artifacts(db, run_id)
    report_artifact = next((item for item in artifacts if item.name == "report.html"), None)
    if report_artifact is None:
        raise HTTPException(status_code=404, detail="Report artifact not found.")
    report_path = request.app.state.storage_root / report_artifact.relative_path
    return HTMLResponse(report_path.read_text(encoding="utf-8"))
