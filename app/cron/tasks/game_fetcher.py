import asyncio
import datetime
import logging

import dateutil.parser
from sqlalchemy.dialects import postgresql as pg_dialect
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.utils import sqla as sqla_utils

from .base import AsyncComponent

logger = logging.getLogger(__name__)


class GameFetcherTask(AsyncComponent):
    def __init__(self, app_ctx: AppCtx) -> None:
        self.app_ctx = app_ctx

        self._game_fetcher_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._game_fetcher_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._game_fetcher_task is not None:
            self._game_fetcher_task.cancel()
            try:
                await self._game_fetcher_task
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

            await asyncio.sleep(3600)

    async def _run_internal(self) -> None:
        try:
            async with bind_app_ctx(self.app_ctx):
                try:
                    await sqla_utils.obtain_advisory_lock(
                        sqla_utils.AdvisoryLockGameFetcherTask(),
                        nowait=True,
                    )
                except Exception:
                    return

                current_date = datetime.datetime.now(tz=datetime.UTC).strftime(
                    "%Y-%m-%d"
                )
                logger.info("Fetching games for date = %s", current_date)

                games = AppCtx.current.balldontlie_api.mlb.games.list(
                    dates=[current_date]
                ).data
                logger.info("Fetched %d games", len(games))

                if not games:
                    return

                result = await AppCtx.current.db.session.execute(
                    pg_dialect.insert(m.Game)
                    .values(
                        [
                            {
                                "balldontlie_id": game.id,
                                "away_id": await self._get_team_id(game.away_team.id),
                                "home_id": await self._get_team_id(game.home_team.id),
                                "start_time": dateutil.parser.isoparse(game.date),
                                "end_time": None,
                                "box_score": None,
                                "rhe": None,
                                "status": game.status,
                                "is_scorhegami": None,
                                "bref_url": None,
                            }
                            for game in games
                        ]
                    )
                    .on_conflict_do_nothing(index_elements=[m.Game.balldontlie_id])
                )
                logger.info("Inserted %d new games", result.rowcount)

                await AppCtx.current.db.session.commit()

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    async def _get_team_id(self, balldontlie_team_id: int) -> int:
        return (
            await AppCtx.current.db.session.execute(
                sa_exp.select(m.Team.id).where(
                    m.Team.balldontlie_id == balldontlie_team_id
                )
            )
        ).scalar_one()

    def is_healthy(self) -> bool:
        if not (
            self._game_fetcher_task is not None and not self._game_fetcher_task.done()
        ):
            return False

        return True
