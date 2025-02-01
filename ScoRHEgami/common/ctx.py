from __future__ import annotations

import contextvars
import dataclasses

from sqlalchemy import create_engine
from ScoRHEgami.common.settings import AppSettings
from sqlalchemy.orm import Session, sessionmaker

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
    db: Session


def create_ctx(app_settings: AppSettings) -> AppCtx:
    engine = create_engine(app_settings.DB_URI)
    SessionLocal = sessionmaker(bind=engine)

    return AppCtx(
        ctx_id="",
        settings=app_settings,
        db=SessionLocal(),
    )


create_ctx()
