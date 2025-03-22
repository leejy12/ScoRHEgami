import asyncio
import logging

from sqlalchemy import func as sa_func
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.utils import sqla as sqla_utils

from .base import AsyncComponent

logger = logging.getLogger(__name__)


class SampleTask(AsyncComponent):
    def __init__(self, app_ctx: AppCtx) -> None:
        self.app_ctx = app_ctx

        self._sample_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._sample_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._sample_task is not None:
            self._sample_task.cancel()
            try:
                await self._sample_task
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

            await asyncio.sleep(10)

    async def _run_internal(self) -> None:
        try:
            async with bind_app_ctx(self.app_ctx):
                try:
                    await sqla_utils.obtain_advisory_lock(
                        sqla_utils.AdvisoryLockSampleTask(),
                        nowait=True,
                    )
                except Exception:
                    return

                teams_cnt = (
                    await AppCtx.current.db.execute(
                        sa_exp.select(sa_func.count()).select_from(m.Team)
                    )
                ).scalar() or 0

                logger.info("There are %d teams.", teams_cnt)

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    def is_healthy(self) -> bool:
        if not (self._sample_task is not None and not self._sample_task.done()):
            return False

        return True
