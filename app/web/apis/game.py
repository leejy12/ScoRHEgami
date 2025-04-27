import datetime

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func
from sqlalchemy import orm as sa_orm
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx
from app.common.models import orm as m
from app.common.models.app import GameStatusEnum, TeamModel

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/latest_completed_date")
async def _() -> datetime.date:
    """
    Returns the most recent date when all games on that date have completed or were postponed.
    In other words, the most recent date with no games in STATUS_SCHEDULED or STATUS_IN_PROGRESS.
    """

    dates_with_pending_games = (
        (
            await AppCtx.current.db.session.execute(
                sa_exp.select(m.Game.game_date)
                .where(
                    (m.Game.status == GameStatusEnum.status_scheduled)
                    | (m.Game.status == GameStatusEnum.status_in_progress)
                )
                .distinct()
            )
        )
        .scalars()
        .all()
    )

    most_recent_completed_date = (
        await AppCtx.current.db.session.execute(
            sa_exp.select(m.Game.game_date)
            .where(m.Game.game_date.notin_(dates_with_pending_games))
            .order_by(m.Game.game_date.desc())
            .limit(1)
        )
    ).scalar_one()

    return most_recent_completed_date


class GameCountRequest(BaseModel):
    is_scorhegami: bool | None = None


@router.get("/count")
async def _(
    q: GameCountRequest = Depends(),
    rhe: list[int] | None = Query(None),
) -> int:
    if rhe is not None:
        if len(rhe) != 6:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    count_query = sa_exp.select(sa_func.count()).select_from(m.Game)

    if rhe is not None:
        count_query = count_query.where(m.Game.rhe == rhe)

    if q.is_scorhegami is not None:
        count_query = count_query.where(m.Game.is_scorhegami.is_(q.is_scorhegami))

    count = (await AppCtx.current.db.session.execute(count_query)).scalar() or 0

    return count


class GameGetRequest(BaseModel):
    offset: int
    count: int = Field(ge=1, le=50)
    filter_date: datetime.date | None = None


class GameGetResponse(BaseModel):
    id: int
    balldontlie_id: int | None
    away_team: TeamModel
    home_team: TeamModel
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    status: GameStatusEnum
    box_score: list[int] | None
    rhe: list[int] | None
    is_scorhegami: bool | None
    bref_url: str | None
    date: datetime.date


@router.get("")
async def _(
    q: GameGetRequest = Depends(),
    rhe: list[int] | None = Query(None),
    filter_statuses: list[GameStatusEnum] | None = Query(None),
) -> list[GameGetResponse]:
    if rhe is not None:
        if len(rhe) != 6:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    games_query = sa_exp.select(m.Game).options(
        sa_orm.joinedload(m.Game.away_team),
        sa_orm.joinedload(m.Game.home_team),
    )

    if rhe is not None:
        games_query = games_query.where(m.Game.rhe == rhe)

    if q.filter_date is not None:
        games_query = games_query.where(m.Game.game_date == q.filter_date)

    if filter_statuses is not None:
        games_query = games_query.where(m.Game.status.in_(filter_statuses))

    games = (
        (
            await AppCtx.current.db.session.execute(
                games_query.order_by(m.Game.start_time.desc())
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
            balldontlie_id=game.balldontlie_id,
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
            status=game.status,
            box_score=game.box_score,
            rhe=game.rhe,
            is_scorhegami=game.is_scorhegami,
            bref_url=game.bref_url,
            date=game.game_date,
        )
        for game in games
    ]


@router.get("/{game_id}")
async def _(game_id: int) -> GameGetResponse:
    game = (
        await AppCtx.current.db.session.execute(
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
        balldontlie_id=game.balldontlie_id,
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
        status=game.status,
        box_score=game.box_score,
        rhe=game.rhe,
        is_scorhegami=game.is_scorhegami,
        bref_url=game.bref_url,
        date=game.game_date,
    )
