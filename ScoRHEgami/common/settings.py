from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    DB_SCHEMA: str = Field(
        default="public",
    )

    DB_URI: AnyUrl = Field(
        default=AnyUrl(
            "postgresql+asyncpg://scorhegami:devpassword@127.0.0.1:5432/scorhegami"
        ),
    )
