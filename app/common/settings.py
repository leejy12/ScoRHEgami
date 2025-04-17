import uuid
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    DB_SCHEMA: str = Field(
        default="public",
    )

    DB_URI: str = Field(
        default="postgresql+asyncpg://scorhegami:devpassword@127.0.0.1:5432/scorhegami",
    )

    DB_OPTIONS: dict[str, Any] = Field(
        default={
            "pool_recycle": 60 * 60,
        }
    )

    BALLDONTLIE_API_KEY: uuid.UUID

    X_API_KEY: str = Field(
        default="",
        description="Consumer Keys > API Key",
    )

    X_API_SECRET: str = Field(
        default="",
        description="Consumer Keys > API Secret",
    )

    X_API_ACCESS_TOKEN: str = Field(
        default="",
        description="Authentication Tokens > Access Token",
    )

    X_API_ACCESS_TOKEN_SECRET: str = Field(
        default="",
        description="Authentication Tokens > Access Token Secret",
    )

    DISABLE_TWEETS: bool = Field(
        default=False,
        description="Option to disable posting to X",
    )

    SENTRY_DSN: str = Field(
        default="",
        description="Sentry DSN URL",
    )
