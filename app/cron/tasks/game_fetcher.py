import asyncio
import datetime
import logging

from balldontlie.mlb.models import MLBGame
from balldontlie.exceptions import BallDontLieException
from sqlalchemy.dialects import postgresql as pg_dialect
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.models.app import CronTaskEnum
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

                now = datetime.datetime.now(tz=datetime.UTC)

                cursor = (
                    await AppCtx.current.db.session.execute(
                        sa_exp.select(m.Cursor).where(
                            m.Cursor.task_name == CronTaskEnum.game_fetcher
                        )
                    )
                ).scalar_one_or_none()

                if cursor is None:
                    cursor = m.Cursor(
                        task_name=CronTaskEnum.game_fetcher.value, last_completed=now
                    )
                    AppCtx.current.db.session.add(cursor)
                    await AppCtx.current.db.session.flush()

                dates = self._get_dates_between(cursor.last_completed, now)

                await AppCtx.current.db.session.execute(
                    sa_exp.update(m.Cursor).values(last_completed=now)
                )

                logger.info("Fetching games for dates = %s", dates)

                try:
                    games = self._get_games_for_dates(dates)
                except BallDontLieException as e:
                    logger.error(
                        f"Failed to fetch games (dates = {dates}): "
                        f"message={e}, status_code={e.status_code}, response={e.response_data}"
                    )
                    return

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
                                "start_time": None,
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

    def _get_games_for_dates(self, dates: list[str]) -> list[MLBGame]:
        game_list = []
        next_cursor = None

        while True:
            list_resp = AppCtx.current.balldontlie_api.mlb.games.list(
                cursor=next_cursor, dates=dates
            )
            game_list.extend(list_resp.data)
            next_cursor = list_resp.meta.next_cursor

            if next_cursor is None:
                return game_list

    async def _get_team_id(self, balldontlie_team_id: int) -> int:
        return (
            await AppCtx.current.db.session.execute(
                sa_exp.select(m.Team.id).where(
                    m.Team.balldontlie_id == balldontlie_team_id
                )
            )
        ).scalar_one()

    def _get_dates_between(
        self,
        start_timestamp: datetime.datetime,
        end_timestamp: datetime.datetime,
    ):
        start_date = start_timestamp.date()
        end_date = end_timestamp.date()

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        num_days = (end_date - start_date).days + 1

        return [
            (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(num_days)
        ]

    def is_healthy(self) -> bool:
        if not (
            self._game_fetcher_task is not None and not self._game_fetcher_task.done()
        ):
            return False

        return True
