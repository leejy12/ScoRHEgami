import asyncio
import logging

from sqlalchemy import func as sa_func
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
                    ).scalar() or 0

                    game.is_scorhegami = rhe_cnt == 1

                    # TODO: Schedule a POST on X.

                await AppCtx.current.db.session.commit()

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    def is_healthy(self) -> bool:
        if not (
            self._scorhegami_updater_task is not None
            and not self._scorhegami_updater_task.done()
        ):
            return False

        return True
