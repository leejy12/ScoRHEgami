import datetime
import asyncio

from sqlalchemy.sql import expression as sa_exp

from app.common.models import orm as m
from app.common.ctx import AppCtx, bind_app_ctx, create_app_ctx
from app.common.settings import AppSettings


async def do_migration():
    results = (
        await AppCtx.current.db.session.execute(
            sa_exp.select(m.Game.id, m.Game.balldontlie_id, m.Game.start_time)
            .where(
                m.Game.start_time >= datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
            )
            .order_by(m.Game.start_time.asc())
        )
    ).all()

    AppCtx.current.db.session.close()

    for i, (game_id, balldontlie_id, start_time) in enumerate(results):
        game = AppCtx.current.balldontlie_api.mlb.games.get(balldontlie_id)

        await AppCtx.current.db.session.execute(
            sa_exp.update(m.Game)
            .values(start_time=game.data.date)
            .where(m.Game.id == game_id)
        )
        await AppCtx.current.db.session.commit()

        print(
            f"[{i:03}] Update game (id={game_id}, balldontlie_id={balldontlie_id}): FROM={start_time}, TO={game.data.date}",
        )

        await asyncio.sleep(3)


async def main():
    app_ctx = await create_app_ctx(AppSettings())
    async with bind_app_ctx(app_ctx):
        await do_migration()


if __name__ == "__main__":
    asyncio.run(main())
