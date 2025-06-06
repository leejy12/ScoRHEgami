import asyncio
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import dateutil
import dateutil.parser
from balldontlie import BalldontlieAPI
from balldontlie.exceptions import BallDontLieException, NotFoundError
from balldontlie.mlb.models import MLBGame
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.models.app import GameStatusEnum

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
                ongoing_game_ids = (
                    await AppCtx.current.db.session.execute(
                        sa_exp.select(m.Game.id, m.Game.balldontlie_id).where(
                            m.Game.status != GameStatusEnum.status_final,
                            m.Game.status != GameStatusEnum.status_postponed,
                        )
                    )
                ).all()

                await AppCtx.current.db.session.close()

                if not ongoing_game_ids:
                    return

                logger.info("Updating %d games", len(ongoing_game_ids))

                try:
                    # Pass the API client object to be shared among threads.
                    game_results = await asyncio.wait_for(
                        self._fetch_all_game_results(
                            [balldontlie_id for _, balldontlie_id in ongoing_game_ids],
                            AppCtx.current.balldontlie_api,
                        ),
                        timeout=60,
                    )
                except TimeoutError:
                    logger.exception("Timeout error when updating games")
                    return

                now = datetime.datetime.now(tz=datetime.UTC)

                for (game_id, balldontlie_id), result in zip(
                    ongoing_game_ids, game_results
                ):
                    if isinstance(result, NotFoundError):
                        logger.warning(
                            "Deleting game id %d due to NotFoundError",
                            game_id,
                        )
                        await AppCtx.current.db.session.execute(
                            sa_exp.delete(m.Game).where(m.Game.id == game_id)
                        )
                        continue
                    elif isinstance(result, BallDontLieException):
                        logger.error(
                            f"Failed to get game result (id = {game_id}, balldontlie_id = {balldontlie_id}): "
                            f"message={result}, status_code={result.status_code}, response={result.response_data}"
                        )
                        continue
                    elif isinstance(result, Exception):
                        logger.error(
                            "Unexpected excepion while getting result of game id %d",
                            game_id,
                        )
                        continue

                    box_score, rhe = self._get_boxscore_and_rhe(result)
                    await AppCtx.current.db.session.execute(
                        sa_exp.update(m.Game)
                        .values(
                            start_time=dateutil.parser.parse(result.date),
                            end_time=now
                            if result.status == GameStatusEnum.status_final
                            else None,
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
        return api.mlb.games.get(balldontlie_game_id).data

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
