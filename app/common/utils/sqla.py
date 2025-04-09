import asyncio
import dataclasses
import hashlib
import random
import time
from typing import Any, Callable

from sqlalchemy import func as sa_func
from sqlalchemy import types as sa_types
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx


class SqlaEngineAndSession:
    def __init__(
        self,
        db_uri: str,
        db_options: dict[str, Any],
        *,
        custom_scope_func: Callable[[], Any] | None = None,
    ) -> None:
        self.engine = create_async_engine(db_uri, **db_options)

        self._scoped_session = async_scoped_session(
            async_sessionmaker(
                self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            ),
            scopefunc=(
                lambda: (
                    AppCtx.current.ctx_id
                    if custom_scope_func is None
                    else custom_scope_func
                )
            ),
        )

    @property
    def session(self) -> AsyncSession:
        return self._scoped_session()

    async def clear_scoped_session(self) -> None:
        await self._scoped_session.remove()


@dataclasses.dataclass
class AdvisoryLockBase:
    @property
    def ident(self) -> str:
        raise NotImplementedError()


@dataclasses.dataclass
class AdvisoryLockSampleTask(AdvisoryLockBase):
    @property
    def ident(self) -> str:
        return "sample_task"


@dataclasses.dataclass
class AdvisoryLockGameFetcherTask(AdvisoryLockBase):
    @property
    def ident(self) -> str:
        return "game_fetcher_task"


@dataclasses.dataclass
class AdvisoryLockGameUpdaterTask(AdvisoryLockBase):
    @property
    def ident(self) -> str:
        return "game_updater_task"


@dataclasses.dataclass
class AdvisoryLockScorhegamiUpdaterTask(AdvisoryLockBase):
    @property
    def ident(self) -> str:
        return "scorhegami_updater_task"


@dataclasses.dataclass
class AdvisoryLockTweeterTask(AdvisoryLockBase):
    @property
    def ident(self) -> str:
        return "tweeter_task"


async def obtain_advisory_lock(
    lock: AdvisoryLockBase,
    timeout: float = 5.0,
    nowait: bool = False,
) -> None:
    ident_hashed = int.from_bytes(
        hashlib.sha256(lock.ident.encode()).digest()[:8],
        byteorder="little",
        signed=True,
    )

    lock_query = sa_exp.select(
        sa_func.pg_try_advisory_xact_lock(
            sa_exp.cast(ident_hashed, sa_types.BigInteger)
        )
    )

    deadline = time.monotonic() + timeout

    while deadline >= time.monotonic():
        is_lock_obtained = (
            await AppCtx.current.db.session.execute(lock_query)
        ).scalar()

        if is_lock_obtained:
            break

        if nowait:
            raise RuntimeError(f"the lock is not acquired at once (lock: {lock})")

        await asyncio.sleep(random.uniform(0.1, 0.2))

    else:
        raise RuntimeError(f"failed to obtain the advisory lock (lock: {lock})")
