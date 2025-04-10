from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx
from app.common.models import orm as m

router = APIRouter(prefix="/team", tags=["team"])


class TeamGetRequest(BaseModel):
    offset: int
    count: int = Field(ge=1, le=10)


class TeamGetResponse(BaseModel):
    id: int
    short_name: str | None
    name: str


@router.get("")
async def _(
    q: TeamGetRequest = Depends(),
) -> list[TeamGetResponse]:
    teams = (
        (
            await AppCtx.current.db.session.execute(
                sa_exp.select(m.Team)
                .order_by(m.Team.id.asc())
                .offset(q.offset)
                .limit(q.count)
            )
        )
        .scalars()
        .all()
    )

    return [
        TeamGetResponse(
            id=team.id,
            short_name=team.short_name,
            name=team.name,
        )
        for team in teams
    ]


@router.get("/{team_id}")
async def _(team_id: int) -> TeamGetResponse:
    team = (
        await AppCtx.current.db.session.execute(
            sa_exp.select(m.Team).where(m.Team.id == team_id)
        )
    ).scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id {team_id} not found",
        )

    return TeamGetResponse(
        id=team.id,
        short_name=team.short_name,
        name=team.name,
    )
