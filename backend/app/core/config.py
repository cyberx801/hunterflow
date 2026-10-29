"""Application configuration.

Secrets and runtime parameters come from environment variables (prefix HF_) or an
.env file. Defaults are safe for local development; production (Docker Compose)
sets explicit values via .env. See .env.example at the repo root.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HF_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    secret_key: str = "dev-only-insecure-secret-key"

    # Database: PostgreSQL is the supported runtime (ADR-005). SQLite is a
    # development-only convenience when no URL is provided.
    database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    data_dir: Path = Path("data")
    evidence_max_mb: int = 50
    evidence_retention_days: int = 0
    tool_timeout_seconds: int = 600
    max_scan_concurrency: int = 1
    session_ttl_days: int = 7
    login_rate_limit_per_minute: int = 5
    cors_origins: list[str] = Field(default_factory=list)

    bootstrap_username: str | None = None
    bootstrap_password: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.env == "development":
            return "sqlite+pysqlite:///./hunterflow-dev.db"
        raise RuntimeError("HF_DATABASE_URL must be set outside development")

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def ensure_data_dirs(self) -> None:
        for sub in ("evidence", "runs"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
