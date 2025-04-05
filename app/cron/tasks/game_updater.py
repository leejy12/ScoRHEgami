import asyncio
import datetime
import dateutil
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from balldontlie import BalldontlieAPI
from balldontlie.exceptions import NotFoundError
from balldontlie.mlb.models import MLBGame
import dateutil.parser
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

            await asyncio.sleep(60)

    async def _run_internal(self) -> None:
        try:
            async with bind_app_ctx(self.app_ctx):
                try:
                    await sqla_utils.obtain_advisory_lock(
                        sqla_utils.AdvisoryLockGameUpdaterTask(),
                        nowait=True,
                    )
                except Exception as e:
                    logger.error("%s", str(e))
                    return

                # TODO: handle games that are cancelled.
                ongoing_games = (
                    (
                        await AppCtx.current.db.session.execute(
                            sa_exp.select(m.Game).where(m.Game.status != "STATUS_FINAL")
                        )
                    )
                    .scalars()
                    .all()
                )

                if not ongoing_games:
                    return

                logger.info("Updating %d games", len(ongoing_games))

                # Pass the API client object to be shared among threads.
                game_results = await self._fetch_all_game_results(
                    [game.balldontlie_id for game in ongoing_games],
                    AppCtx.current.balldontlie_api,
                )

                now = datetime.datetime.now(tz=datetime.UTC)

                for game, result in zip(ongoing_games, game_results):
                    if isinstance(result, NotFoundError):
                        logger.warning(
                            "Deleting game id %d due to NotFoundError",
                            game.id,
                        )
                        await AppCtx.current.db.session.execute(
                            sa_exp.delete(m.Game).where(
                                m.Game.balldontlie_id == game.balldontlie_id
                            )
                        )
                        continue
                    elif isinstance(result, Exception):
                        logger.exception("Failed to get result of game id %d", game.id)
                        continue

                    box_score, rhe = self._get_boxscore_and_rhe(result)
                    await AppCtx.current.db.session.execute(
                        sa_exp.update(m.Game)
                        .values(
                            start_time=dateutil.parser.parse(result.date),
                            end_time=now if result.status == "STATUS_FINAL" else None,
                            status=result.status,
                            box_score=box_score,
                            rhe=rhe,
                        )
                        .where(m.Game.balldontlie_id == result.id)
                    )

                await AppCtx.current.db.session.commit()

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    async def _fetch_all_game_results(
        self, game_ids: list[int], api: BalldontlieAPI
    ) -> list[MLBGame | Exception]:
        coroutines = [self._fetch_game_result(game_id, api) for game_id in game_ids]

        return await asyncio.gather(*coroutines, return_exceptions=True)

    async def _fetch_game_result(self, game_id: int, api: BalldontlieAPI) -> MLBGame:
        loop = asyncio.get_running_loop()

        fn = partial(self._get_game_result, game_id, api)
        return await loop.run_in_executor(self.pool, fn)

    def _get_game_result(
        self, balldontlie_game_id: int, api: BalldontlieAPI
    ) -> MLBGame:
        try:
            return api.mlb.games.get(balldontlie_game_id).data
        except Exception as e:
            logger.error(f"Failed to get game result for ID {balldontlie_game_id}: {e}")
            raise

    def _get_boxscore_and_rhe(self, result: MLBGame) -> tuple[list[int], list[int]]:
        away_team_scores = result.away_team_data.inning_scores
        home_team_scores = result.home_team_data.inning_scores

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
