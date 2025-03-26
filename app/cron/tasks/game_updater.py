import datetime
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from balldontlie.mlb.models import MLBGame
from sqlalchemy import Tuple
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.utils import sqla as sqla_utils

from .base import AsyncComponent

logger = logging.getLogger(__name__)


class GameUpdaterTask(AsyncComponent):
    def __init__(self, app_ctx: AppCtx) -> None:
        self.app_ctx = app_ctx

        self._game_updater_task: asyncio.Task | None = None
        self.pool = ThreadPoolExecutor(max_workers=4)

    async def start(self) -> None:
        self._game_updater_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._game_updater_task is not None:
            self._game_updater_task.cancel()
            try:
                await self._game_updater_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.warning(
                    "exception from %s",
                    self.__class__.__name__,
                    exc_info=True,
                )
            finally:
                self.pool.shutdown(wait=False)

    async def _run(self) -> None:
        while True:
            await self._run_internal()

            await asyncio.sleep(30)

    async def _run_internal(self) -> None:
        try:
            async with bind_app_ctx(self.app_ctx):
                try:
                    await sqla_utils.obtain_advisory_lock(
                        sqla_utils.AdvisoryLockGameUpdaterTask(),
                        nowait=True,
                    )
                except Exception:
                    return

                ongoing_games = (
                    (
                        await AppCtx.current.db.execute(
                            sa_exp.select(m.Game).where(m.Game.status != "STATUS_FINAL")
                        )
                    )
                    .scalars()
                    .all()
                )

                if not ongoing_games:
                    return

                game_results = await self._fetch_all_game_results(
                    [game.balldontlie_id for game in ongoing_games]
                )

                game_results = [
                    result for result in game_results if result.status == "STATUS_FINAL"
                ]

                now = datetime.datetime.now(tz=datetime.UTC)

                for result in game_results:
                    boxscore, rhe = self._get_boxscore_and_rhe(result)
                    await AppCtx.current.db.execute(
                        sa_exp.update(m.Game)
                        .values(
                            end_time=now,
                            boxscore=boxscore,
                            rhe=rhe,
                        )
                        .where(m.Game.balldontlie_id == result.id)
                    )

                await AppCtx.current.db.commit()

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    async def _fetch_all_game_results(self, game_ids: list[int]) -> list[MLBGame]:
        coroutines = [self._fetch_game_result(game_id) for game_id in game_ids]

        return await asyncio.gather(*coroutines, return_exceptions=True)

    async def _fetch_game_result(self, game_id: int) -> MLBGame:
        loop = asyncio.get_running_loop()

        fn = partial(self._get_game_result, game_id)
        return await loop.run_in_executor(self.pool, fn)

    def _get_game_result(self, balldontlie_game_id: int) -> MLBGame:
        try:
            return AppCtx.current.balldontlie_api.mlb.games.get(
                balldontlie_game_id
            ).data
        except Exception as e:
            logger.error(f"Failed to get game result for ID {balldontlie_game_id}: {e}")
            raise

    def _get_boxscore_and_rhe(self, result: MLBGame) -> Tuple[list[int], list[int]]:
        away_team_scores = result.away_team_data.inning_scores
        home_team_scores = result.away_team_data.inning_scores

        if len(away_team_scores) > len(home_team_scores):
            home_team_scores.append(0)

        away_team_rhe = [
            result.away_team_data.runs,
            result.away_team_data.hits,
            result.away_team_data.errors,
        ]

        home_team_rhe = [
            result.home_team_data.runs,
            result.home_team_data.hits,
            result.home_team_data.errors,
        ]

        box_score = away_team_scores + away_team_rhe + home_team_scores + home_team_rhe
        rhe = away_team_rhe + home_team_rhe

        return (box_score, rhe)

    def is_healthy(self) -> bool:
        if not (
            self._game_updater_task is not None and not self._game_updater_task.done()
        ):
            return False

        return True
