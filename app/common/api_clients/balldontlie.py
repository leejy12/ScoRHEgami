from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    data: T


class ListResponse(BaseResponse[list[T]]):
    pass


class PaginationMeta(BaseModel):
    per_page: int | None = None
    next_cursor: int | None = None


class PaginatedListResponse(BaseResponse[list[T]]):
    meta: PaginationMeta


class MLBTeam(BaseModel):
    id: int
    slug: str
    abbreviation: str
    display_name: str
    short_display_name: str
    name: str
    location: str
    league: str
    division: str


class MLBGameTeamData(BaseModel):
    hits: int | None = None
    runs: int | None = None
    errors: int | None = None
    inning_scores: list[int] | None = None


class MLBGameScoringSummary(BaseModel):
    play: str
    inning: str
    period: str
    away_score: int
    home_score: int


class MLBGame(BaseModel):
    id: int
    home_team_name: str
    away_team_name: str
    home_team: MLBTeam
    away_team: MLBTeam
    season: int
    postseason: bool
    season_type: str | None = None
    date: str
    home_team_data: MLBGameTeamData | None = None
    away_team_data: MLBGameTeamData | None = None
    venue: str | None = None
    attendance: int | None = None
    conference_play: bool | None = None
    status: str | None = None
    period: int | None = None
    clock: int | None = None
    display_clock: str | None = None
    scoring_summary: list[MLBGameScoringSummary] | None = None


class BalldontlieAPI:
    def __init__(self, url: str, api_key: str):
        self.client = httpx.AsyncClient()
        self.url = url
        self.api_key = api_key

    def _prepare_params(self, params: dict[str, Any]) -> dict[str, list[str]]:
        processed = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, list):
                processed[f"{key}[]"] = [str(item) for item in value]
            else:
                processed[key] = [str(value)]
        return processed

    async def get_mlb_games(
        self,
        *,
        cursor: int | None = None,
        per_page: int | None = None,
        dates: list[str] | None = None,
        seasons: list[int] | None = None,
        team_ids: list[int] | None = None,
        postseason: bool | None = None,
        season_type: str | None = None,
    ) -> PaginatedListResponse[MLBGame]:
        params = self._prepare_params(
            {
                "cursor": cursor,
                "per_page": per_page,
                "dates": dates,
                "seasons": seasons,
                "team_ids": team_ids,
                "postseason": postseason,
                "season_type": season_type,
            }
        )

        response = await self.client.get(
            f"{self.url}/mlb/v1/games",
            params=params,
            headers={"Authorization": self.api_key},
        )
        response.raise_for_status()

        return PaginatedListResponse[MLBGame].model_validate(response.json())

    async def get_mlb_game(self, game_id: int) -> BaseResponse[MLBGame]:
        response = await self.client.get(
            f"{self.url}/mlb/v1/games/{game_id}",
            headers={"Authorization": self.api_key},
        )
        response.raise_for_status()

        return BaseResponse[MLBGame].model_validate(response.json())
