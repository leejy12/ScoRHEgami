from pydantic import BaseModel


class TeamModel(BaseModel):
    id: int
    short_name: str | None
    name: str
