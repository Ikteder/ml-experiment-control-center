from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .api.routes import router
from .core.config import settings
from .core.database import Base, SessionLocal, engine, get_db
from .services.runner import RunOrchestrator


def create_app(
    *,
    database_engine: Engine = engine,
    session_factory: sessionmaker[Session] = SessionLocal,
    storage_root: Path = settings.storage_root,
    step_delay_seconds: float = settings.run_step_delay_seconds,
) -> FastAPI:
    storage_root.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        Base.metadata.create_all(bind=database_engine)
        application.state.runner = RunOrchestrator(
            session_factory,
            storage_root=storage_root,
            step_delay_seconds=step_delay_seconds,
            source_revision=settings.source_revision,
        )
        application.state.runner.recover_interrupted_runs()
        application.state.storage_root = storage_root
        yield
        application.state.runner.shutdown()

    application = FastAPI(
        title=settings.app_name,
        version="1.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.mount("/storage", StaticFiles(directory=storage_root), name="storage")
    application.include_router(router, prefix=settings.api_prefix)

    if session_factory is not SessionLocal:
        def isolated_session() -> Generator[Session, None, None]:
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        application.dependency_overrides[get_db] = isolated_session

    return application


app = create_app()
