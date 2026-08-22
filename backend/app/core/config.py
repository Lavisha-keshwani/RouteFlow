"""Application configuration loaded from environment variables.

All configuration is environment-driven so the application can be deployed to
different targets (local, Render, Railway) without code changes. No business
rates or secrets are hardcoded here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    APP_NAME: str = "RouteFlow"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://routeflow:routeflow@localhost:5432/routeflow",
        description="SQLAlchemy database URL.",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True

    # --- Security / JWT ---
    JWT_SECRET: str = Field(default="change-me-in-production", min_length=8)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24
    JWT_REFRESH_EXPIRATION_MINUTES: int = 60 * 24 * 7

    # --- CORS ---
    # ``NoDecode`` prevents pydantic-settings from JSON-decoding the raw value so
    # the validator below can accept a simple comma-separated string from .env.
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Notifications ---
    EMAIL_ENABLED: bool = True
    EMAIL_PROVIDER: str = "console"  # console | smtp | resend
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@routeflow.app"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    SMS_ENABLED: bool = False
    SMS_PROVIDER: str = "console"  # console | twilio
    SMS_API_KEY: str = ""
    SMS_API_SECRET: str = ""
    SMS_FROM: str = ""

    # --- Geocoding (optional) ---
    GEOCODING_ENABLED: bool = False
    GEOCODING_PROVIDER: str = "nominatim"
    GEOCODING_API_KEY: str = ""

    # --- Business defaults (non-rate configuration only) ---
    VOLUMETRIC_DIVISOR: int = 5000
    ORDER_ID_PREFIX: str = "RF"
    MAX_RESCHEDULE_ATTEMPTS: int = 3
    RATE_LIMIT_PER_MINUTE: int = 120

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Allow CORS origins to be provided as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
