from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    DB_SCHEMA: str = Field(
        default="public",
    )

    DB_URI: str = Field(
        default="postgresql+psycopg2://scorhegami:devpassword@127.0.0.1:5432/scorhegami",
    )
