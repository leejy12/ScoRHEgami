from typing import Any
import uuid

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
