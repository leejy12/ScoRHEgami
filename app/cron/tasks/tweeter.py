import asyncio
import datetime
import logging

import tweepy
import tweepy.errors
from sqlalchemy import func as sa_func
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx, bind_app_ctx
from app.common.models import orm as m
from app.common.models.app import TweetStatusEnum
from app.common.utils import sqla as sqla_utils

from .base import AsyncComponent

# X API Free tier limits tweet posting to 17 tweets per 24-hour period.
_MAX_TWEETS_PER_DAY = 17


logger = logging.getLogger(__name__)


class TweeterTask(AsyncComponent):
    def __init__(self, app_ctx: AppCtx) -> None:
        self.app_ctx = app_ctx

        self._tweeter_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._tweeter_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._tweeter_task is not None:
            self._tweeter_task.cancel()
            try:
                await self._tweeter_task
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
                        sqla_utils.AdvisoryLockTweeterTask(),
                        nowait=True,
                    )
                except Exception as e:
                    logger.error("%s", str(e))
                    return

                if not (await self._under_rate_limit()):
                    return

                tweet = (
                    await AppCtx.current.db.session.execute(
                        sa_exp.select(m.Tweet)
                        .where(m.Tweet.status == TweetStatusEnum.pending)
                        .order_by(m.Tweet.created_at.asc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if tweet is None:
                    return

                try:
                    logger.info("Posting tweet for game %d", tweet.game_id)

                    if not self.app_ctx.settings.DISABLE_TWEETS:
                        resp = await AppCtx.current.x_api.create_tweet(
                            text=tweet.content
                        )
                        tweet_id: str = resp.data["id"]

                        logger.info(
                            "Successfully posted tweet for game %d (tweet id = %s)",
                            tweet.game_id,
                            tweet_id,
                        )
                        tweet.tweet_id = tweet_id
                        tweet.status = TweetStatusEnum.success
                        tweet.posted_at = datetime.datetime.now(tz=datetime.UTC)
                    else:
                        logger.info("Tweeting is disabled")
                        tweet.status = TweetStatusEnum.skipped
                        tweet.posted_at = datetime.datetime.now(tz=datetime.UTC)

                except tweepy.errors.HTTPException as e:
                    tweet.status = TweetStatusEnum.failed
                    tweet.tweet_failed_reason = str(e)

                    logger.error(
                        "Failed to post tweet for game %d, reason = %s",
                        tweet.game_id,
                        tweet.tweet_failed_reason,
                    )

                await AppCtx.current.db.session.commit()

        except Exception:
            logger.exception(f"Failed to run {self.__class__.__name__}")

    async def _under_rate_limit(self) -> bool:
        if self.app_ctx.settings.DISABLE_TWEETS:
            return True

        now = datetime.datetime.now(tz=datetime.UTC)
        tweet_cnt = (
            await AppCtx.current.db.session.execute(
                sa_exp.select(sa_func.count())
                .select_from(m.Tweet)
                .where(
                    m.Tweet.posted_at > now - datetime.timedelta(hours=24),
                )
            )
        ).scalar() or 0

        return tweet_cnt < _MAX_TWEETS_PER_DAY

    def is_healthy(self) -> bool:
        if not (self._tweeter_task is not None and not self._tweeter_task.done()):
            return False

        return True
