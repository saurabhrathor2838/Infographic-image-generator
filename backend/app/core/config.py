"""
Application configuration settings.

All settings are loaded from environment variables (optionally via a ``.env``
file).  No secrets are hard-coded here — placeholders live in ``.env.example``
at the project root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the project root so .env can be found regardless of CWD.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
ENV_FILE: Path = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Top-level application settings.

    Environment variables are read in order of precedence:
      1. Actual environment variables
      2. ``.env`` file (if present)
      3. Default values below
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # ── AI Provider ──────────────────────────────────────────────────────
    ai_provider: str = Field(default="", alias="AI_PROVIDER")
    text_model: str = Field(default="", alias="TEXT_MODEL")
    image_provider: str = Field(default="", alias="IMAGE_PROVIDER")
    image_model: str = Field(default="", alias="IMAGE_MODEL")

    # ── Provider API Keys (optional at runtime) ──────────────────────────
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    stability_api_key: Optional[str] = Field(default=None, alias="STABILITY_API_KEY")

    # ── AWS / Bedrock ────────────────────────────────────────────────────
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, alias="AWS_SECRET_ACCESS_KEY"
    )
    aws_default_region: str = Field(default="us-east-1", alias="AWS_DEFAULT_REGION")

    # ── Database / Storage ───────────────────────────────────────────────
    database_url: str = Field(default="", alias="DATABASE_URL")
    max_agent_retries: int = Field(default=3, alias="MAX_AGENT_RETRIES")

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    s3_bucket_name: Optional[str] = Field(default=None, alias="S3_BUCKET_NAME")
    s3_region: Optional[str] = Field(default=None, alias="S3_REGION")

    # ── Frontend ─────────────────────────────────────────────────────────
    next_public_api_url: str = Field(
        default="http://localhost:8000", alias="NEXT_PUBLIC_API_URL"
    )

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")


# Module-level singleton — import `settings` everywhere.
settings: Settings = Settings()
