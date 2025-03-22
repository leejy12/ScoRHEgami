import datetime

from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.sql import expression as sa_exp
from sqlalchemy import orm as sa_orm

from app.common.ctx import AppCtx
from app.common.models import orm as m
from app.common.models.app import TeamModel

router = APIRouter(prefix="/game", tags=["game"])


class GameGetRequest(BaseModel):
    offset: int
    count: int = Field(ge=1, le=10)


class GameGetResponse(BaseModel):
    id: int
    away_team: TeamModel
    home_team: TeamModel
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    box_score: list[int]
    rhe: list[int]
    is_scorhegami: bool


@router.get("")
async def _(
    q: GameGetRequest = Depends(),
) -> list[GameGetResponse]:
    games = (
        (
            await AppCtx.current.db.execute(
                sa_exp.select(m.Game)
                .options(
                    sa_orm.joinedload(m.Game.away_team),
                    sa_orm.joinedload(m.Game.home_team),
                )
                .order_by(m.Game.id.asc())
                .offset(q.offset)
                .limit(q.count)
            )
        )
        .scalars()
        .all()
    )

    return [
        GameGetResponse(
            id=game.id,
            away_team=TeamModel(
                id=game.away_team.id,
                short_name=game.away_team.short_name,
                name=game.away_team.name,
            ),
            home_team=TeamModel(
                id=game.home_team.id,
                short_name=game.home_team.short_name,
                name=game.home_team.name,
            ),
            start_time=game.start_time,
            end_time=game.end_time,
            box_score=game.box_score,
            rhe=game.rhe,
            is_scorhegami=game.is_scorhegami,
        )
        for game in games
    ]


@router.get("/{game_id}")
async def _(game_id: int) -> GameGetResponse:
    game = (
        await AppCtx.current.db.execute(
            sa_exp.select(m.Game)
            .options(
                sa_orm.joinedload(m.Game.away_team), sa_orm.joinedload(m.Game.home_team)
            )
            .where(m.Game.id == game_id)
        )
    ).scalar_one_or_none()

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with id {game_id} not found",
        )

    return GameGetResponse(
        id=game.id,
        away_team=TeamModel(
            id=game.away_team.id,
            short_name=game.away_team.short_name,
            name=game.away_team.name,
        ),
        home_team=TeamModel(
            id=game.home_team.id,
            short_name=game.home_team.short_name,
            name=game.home_team.name,
        ),
        start_time=game.start_time,
        end_time=game.end_time,
        box_score=game.box_score,
        rhe=game.rhe,
        is_scorhegami=game.is_scorhegami,
    )
