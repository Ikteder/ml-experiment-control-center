from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ML Experiment Control Center"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./app.db"
    host: str = "0.0.0.0"
    port: int = 8000
    default_page_size: int = 10
    max_page_size: int = 50
    log_poll_interval_seconds: float = 0.4
    run_step_delay_seconds: float = 0.12
    storage_root: Path = Path(__file__).resolve().parents[3] / "storage"
    reports_root: Path = Path(__file__).resolve().parents[3] / "docs" / "graphics"

    model_config = SettingsConfigDict(env_prefix="MLECC_", extra="ignore")


settings = Settings()

