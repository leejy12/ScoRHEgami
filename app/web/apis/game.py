import datetime

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func
from sqlalchemy import orm as sa_orm
from sqlalchemy.sql import expression as sa_exp
from sqlalchemy.exc import IntegrityError

from app.common.ctx import AppCtx
from app.common.models import orm as m
from app.common.models.app import TeamModel

router = APIRouter(prefix="/game", tags=["game"])


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

    count = (await AppCtx.current.db.execute(count_query)).scalar() or 0

    return count


class GamePostRequest(BaseModel):
    away_id: int
    home_id: int
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    box_score: list[int]
    bref_url: str | None


class GamePostResponse(BaseModel):
    id: int
    away_team: TeamModel
    home_team: TeamModel
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    box_score: list[int]
    rhe: list[int]
    is_scorhegami: bool
    bref_url: str | None


@router.post("")
async def _(
    q: GamePostRequest,
) -> GamePostResponse:
    away_team = (
        await AppCtx.current.db.execute(
            sa_exp.select(m.Team).where(m.Team.id == q.away_id)
        )
    ).scalar_one_or_none()

    if away_team is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "away team does not exist"},
        )

    home_team = (
        await AppCtx.current.db.execute(
            sa_exp.select(m.Team).where(m.Team.id == q.home_id)
        )
    ).scalar_one_or_none()

    if home_team is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "home team does not exist"},
        )

    N = len(q.box_score)

    if N % 2 != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "box score does not have even number of elements"},
        )

    if N < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "box score does not enough elements"},
        )

    rhe = q.box_score[N // 2 - 3 : N // 2] + q.box_score[N - 3 : N]

    is_scorhegami = not (
        await AppCtx.current.db.scalar(
            sa_exp.select(sa_exp.exists().where(m.Game.rhe == rhe))
        )
        or False
    )

    game = m.Game(
        away_id=q.away_id,
        home_id=q.home_id,
        start_time=q.start_time,
        end_time=q.end_time,
        box_score=q.box_score,
        rhe=rhe,
        is_scorhegami=is_scorhegami,
        bref_url=q.bref_url,
    )

    AppCtx.current.db.add(game)

    try:
        await AppCtx.current.db.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "game already exists"},
        )

    return GameGetResponse(
        id=game.id,
        away_team=TeamModel(
            id=away_team.id,
            short_name=away_team.short_name,
            name=away_team.name,
        ),
        home_team=TeamModel(
            id=home_team.id,
            short_name=home_team.short_name,
            name=home_team.name,
        ),
        start_time=game.start_time,
        end_time=game.end_time,
        box_score=game.box_score,
        rhe=game.rhe,
        is_scorhegami=game.is_scorhegami,
        bref_url=game.bref_url,
    )


class GameGetRequest(BaseModel):
    offset: int
    count: int = Field(ge=1, le=50)


class GameGetResponse(BaseModel):
    id: int
    away_team: TeamModel
    home_team: TeamModel
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    box_score: list[int]
    rhe: list[int]
    is_scorhegami: bool
    bref_url: str | None


@router.get("")
async def _(
    q: GameGetRequest = Depends(),
    rhe: list[int] | None = Query(None),
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

    games = (
        (
            await AppCtx.current.db.execute(
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
            bref_url=game.bref_url,
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
        bref_url=game.bref_url,
    )
