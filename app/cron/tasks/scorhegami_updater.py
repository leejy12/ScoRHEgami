import asyncio
import logging

from sqlalchemy import func as sa_func
from sqlalchemy import orm as sa_orm
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.utils import sqla as sqla_utils

from .base import AsyncComponent

logger = logging.getLogger(__name__)


class ScorhegamiUpdaterTask(AsyncComponent):
    def __init__(self, app_ctx: AppCtx) -> None:
        self.app_ctx = app_ctx

        self._scorhegami_updater_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._scorhegami_updater_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._scorhegami_updater_task is not None:
            self._scorhegami_updater_task.cancel()
            try:
                await self._scorhegami_updater_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.warning(
                    "exception from %s",
                    self.__class__.__name__,
                    exc_info=True,
                )

    async def _run(self) -> None:
        while True:
            await self._run_internal()

            await asyncio.sleep(60)

    async def _run_internal(self) -> None:
        try:
            async with bind_app_ctx(self.app_ctx):
                try:
                    await sqla_utils.obtain_advisory_lock(
                        sqla_utils.AdvisoryLockScorhegamiUpdaterTask(),
                        nowait=True,
                    )
                except Exception as e:
                    logger.error("%s", str(e))
                    return

                games_in_final = (
                    (
                        await AppCtx.current.db.session.execute(
                            sa_exp.select(m.Game)
                            .options(
                                sa_orm.joinedload(m.Game.away_team),
                                sa_orm.joinedload(m.Game.home_team),
                            )
                            .where(
                                m.Game.status == "STATUS_FINAL",
                                m.Game.is_scorhegami.is_(None),
                            )
                            .order_by(m.Game.end_time.desc())
                        )
                    )
                    .scalars()
                    .all()
                )

                if not games_in_final:
                    return

                logger.info(
                    "Updating %d games that have just ended.", len(games_in_final)
                )

                for game in games_in_final:
                    rhe_cnt = (
                        await AppCtx.current.db.session.execute(
                            sa_exp.select(sa_func.count())
                            .select_from(m.Game)
                            .where(m.Game.rhe == game.rhe)
                        )
                    ).scalar_one()

                    game.is_scorhegami = rhe_cnt == 1
                    await AppCtx.current.db.session.flush()

                    try:
                        await self._post_tweet(game, rhe_cnt)
                    except Exception:
                        logger.exception("Failed to post tweet. game_id = %d", game.id)

                await AppCtx.current.db.session.commit()

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    async def _post_tweet(self, game: m.Game, rhe_cnt: int) -> None:
        rhe = game.rhe

        content = "FINAL\n"
        content += "     R  H  E\n"
        content += f"{game.away_team.short_name:3} {rhe[0]:2} {rhe[1]:2} {rhe[2]:2}\n"
        content += f"{game.home_team.short_name:3} {rhe[3]:2} {rhe[4]:2} {rhe[5]:2}\n"

        if game.is_scorhegami:
            content += "\nThat's ScoRHEgami!\n"
            num_scorhegamis = (
                await AppCtx.current.db.session.execute(
                    sa_exp.select(sa_func.count())
                    .select_from(m.Game)
                    .where(m.Game.is_scorhegami.is_(True))
                )
            ).scalar_one()
            content += f"It's the {self._get_ordinal_string(num_scorhegamis)} unique RHE score in history."
        else:
            content += f"\nNot a ScoRHEgami. That score has happened {rhe_cnt - 1} "
            content += ("time" if rhe_cnt == 2 else "times") + " before."
            # TODO: Return the most recent game with that RHE.

        # TODO: Actually post to X.
        end_time = game.end_time.strftime("%Y-%m-%d_%H%M%S")
        with open(
            f"tweets/{game.id}-{end_time}-{game.away_team.short_name}-{game.home_team.short_name}.txt",
            "w",
        ) as f:
            f.write(content)

    def _get_ordinal_string(n: int) -> str:
        if 11 <= (n % 100) <= 13:
            return f"{n}th"

        match n % 10:
            case 1:
                return f"{n}st"
            case 2:
                return f"{n}nd"
            case 3:
                return f"{n}rd"
            case _:
                return f"{n}th"

    def is_healthy(self) -> bool:
        if not (
            self._scorhegami_updater_task is not None
            and not self._scorhegami_updater_task.done()
        ):
            return False

        return True
