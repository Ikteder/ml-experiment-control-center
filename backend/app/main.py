from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core.config import settings
from .core.database import Base, SessionLocal, engine
from .services.runner import RunOrchestrator


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    application.state.runner = RunOrchestrator(SessionLocal)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    yield
    application.state.runner.shutdown()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=settings.storage_root), name="storage")
app.include_router(router, prefix=settings.api_prefix)

