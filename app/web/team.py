from fastapi.routing import APIRouter
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx
from app.common.models import orm as m

router = APIRouter(prefix="/team", tags=["team"])


@router.get("")
async def _():
    teams = (
        (await AppCtx.current.db.execute(sa_exp.select(m.Team).limit(10)))
        .scalars()
        .all()
    )

    return [
        {
            "id": team.id,
            "name": team.name,
        }
        for team in teams
    ]
