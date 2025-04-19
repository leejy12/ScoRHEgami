import enum

from pydantic import BaseModel


class CronTaskEnum(str, enum.Enum):
    game_fetcher = "game_fetcher"


class GameStatusEnum(str, enum.Enum):
    status_scheduled = "STATUS_SCHEDULED"
    status_in_progress = "STATUS_IN_PROGRESS"
    status_final = "STATUS_FINAL"
    status_postponed = "STATUS_POSTPONED"
    status_rain_delay = "STATUS_RAIN_DELAY"


class TeamModel(BaseModel):
    id: int
    short_name: str | None
    name: str


class TweetStatusEnum(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    skipped = "skipped"
