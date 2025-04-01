from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import logging
import uuid
from typing import TYPE_CHECKING, AsyncIterator

import tweepy
from balldontlie import BalldontlieAPI
import tweepy.asynchronous.client

from app.common.settings import AppSettings

if TYPE_CHECKING:
    from .utils.sqla import SqlaEngineAndSession


logger = logging.getLogger(__name__)


_current_app_ctx_var: contextvars.ContextVar[AppCtx] = contextvars.ContextVar(
    "_current_app_ctx_var"
)


class AppCtxMeta(type):
    @property
    def current(self) -> AppCtx:
        return _current_app_ctx_var.get()


@dataclasses.dataclass(frozen=True)
class AppCtx(metaclass=AppCtxMeta):
    ctx_id: str
    settings: AppSettings
    db: SqlaEngineAndSession
    balldontlie_api: BalldontlieAPI
    x_api: tweepy.asynchronous.client.AsyncClient


async def create_app_ctx(app_settings: AppSettings) -> AppCtx:
    from .utils.sqla import SqlaEngineAndSession

    ctx = AppCtx(
        ctx_id=str(uuid.uuid4()),
        settings=app_settings,
        db=SqlaEngineAndSession(app_settings.DB_URI, app_settings.DB_OPTIONS),
        balldontlie_api=BalldontlieAPI(api_key=str(app_settings.BALLDONTLIE_API_KEY)),
        x_api=tweepy.asynchronous.client.AsyncClient(
            consumer_key=app_settings.X_API_KEY,
            consumer_secret=app_settings.X_API_SECRET,
            access_token=app_settings.X_API_ACCESS_TOKEN,
            access_token_secret=app_settings.X_API_ACCESS_TOKEN_SECRET,
        ),
    )

    _current_app_ctx_var.set(ctx)

    return ctx


@contextlib.asynccontextmanager
async def bind_app_ctx(app_ctx: AppCtx) -> AsyncIterator[None]:
    ctx = dataclasses.replace(app_ctx, ctx_id=str(uuid.uuid4()))
    token = _current_app_ctx_var.set(ctx)
    try:
        yield
    finally:
        try:
            await app_ctx.db.clear_scoped_session()
        except Exception:
            logger.warning("Failed to clear DB scoped session", exc_info=True)

        _current_app_ctx_var.reset(token)
