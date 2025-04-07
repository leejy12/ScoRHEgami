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
                            .order_by(m.Game.end_time.asc())
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
        content = await self._get_tweet_content(game, rhe_cnt)

        try:
            logger.info("Posting tweet for game %d", game.id)
            resp = await AppCtx.current.x_api.create_tweet(text=content)
            tweet_id: str = resp.data["id"]

            await AppCtx.current.db.session.execute(
                sa_exp.insert(m.Tweet).values(
                    game_id=game.id,
                    tweet_id=tweet_id,
                    content=content,
                    tweet_failed_reason=None,
                )
            )
            logger.info(
                "Successfully posted tweet for game %d (tweet id = %s)",
                game.id,
                tweet_id,
            )
        except Exception as e:
            await AppCtx.current.db.session.execute(
                sa_exp.insert(m.Tweet).values(
                    game_id=game.id,
                    tweet_id=None,
                    content=content,
                    tweet_failed_reason=str(e),
                )
            )
            logger.error("X API error: %s", str(e))
            raise

    async def _get_tweet_content(self, game: m.Game, rhe_cnt: int) -> str:
        def _add_spaces(short_name: str) -> str:
            if len(short_name) == 2:
                return short_name + "  "
            else:
                return short_name

        rhe = game.rhe

        content = "FINAL\n"
        content += "          R  H  E\n"
        content += f"{_add_spaces(game.away_team.short_name)}  {rhe[0]:2} {rhe[1]:2} {rhe[2]:2}\n"
        content += f"{_add_spaces(game.home_team.short_name)}  {rhe[3]:2} {rhe[4]:2} {rhe[5]:2}\n"

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

        return content

    def _get_ordinal_string(self, n: int) -> str:
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
