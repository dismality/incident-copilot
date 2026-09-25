from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Incident Copilot"
    environment: str = "development"
    database_url: str = "sqlite:///./incident_copilot.db"
    simulator_base_url: str = "http://localhost:8081"
    dashboard_origin: str = "http://localhost:8501"
    agent_mode: str = Field(default="demo", pattern="^(demo|openai)$")
    openai_model: str = "gpt-4.1-mini"
    alertmanager_webhook_token: str = "demo-monitoring-token-change-me"
    alertmanager_auto_investigate: bool = False
    request_timeout_seconds: float = 10.0
    runbook_directory: Path = Path(__file__).resolve().parents[2] / "runbooks"


@lru_cache
def get_settings() -> Settings:
    return Settings()
