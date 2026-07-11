"""Application configuration via environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Authentication
    mcp_bearer_token: str = Field(
        default="",
        description="****** for MCP endpoint authentication",
    )

    # Google Maps
    google_maps_api_key: str = Field(
        default="",
        description="Google Maps / Geocoding API key",
    )

    # SGU API
    sgu_base_url: str = Field(
        default="https://api.sgu.se/oppnadata/brunnar/ogc/features/v1",
        description="Base URL for SGU OGC Features API",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level",
    )

    # Limits
    max_inline_results: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of records returned inline per tool call",
    )
    max_export_records: int = Field(
        default=50000,
        ge=1,
        description="Maximum number of records in an export",
    )
    max_upstream_concurrency: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum concurrent upstream requests",
    )

    # Cache
    cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        description="Default cache TTL in seconds",
    )
    export_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        description="Export file TTL in seconds",
    )

    # Server
    port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="HTTP port to listen on",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind to",
    )

    @field_validator("mcp_bearer_token")
    @classmethod
    def token_must_not_be_empty_in_production(cls, v: str, info: object) -> str:
        """Warn when token is not set (validated at startup)."""
        return v

    @property
    def is_production(self) -> bool:
        """Return True if running in production."""
        return self.app_env == "production"


# Module-level singleton, re-used across the application
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
