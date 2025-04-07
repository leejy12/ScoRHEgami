import enum

from pydantic import BaseModel


class CronTaskEnum(str, enum.Enum):
    game_fetcher = "game_fetcher"


class TeamModel(BaseModel):
    id: int
    short_name: str | None
    name: str


class TweetStatusEnum(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
