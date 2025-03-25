from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import uuid
from typing import AsyncIterator

from balldontlie import BalldontlieAPI

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from app.common.settings import AppSettings

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
    db: AsyncSession
    balldontlie_api: BalldontlieAPI


async def create_app_ctx(app_settings: AppSettings) -> AppCtx:
    engine = create_async_engine(app_settings.DB_URI)
    AsyncSessionLocal = async_sessionmaker(bind=engine)

    ctx = AppCtx(
        ctx_id=str(uuid.uuid4()),
        settings=app_settings,
        db=AsyncSessionLocal(),
        balldontlie_api=BalldontlieAPI(api_key=str(app_settings.BALLDONTLIE_API_KEY)),
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
        _current_app_ctx_var.reset(token)
