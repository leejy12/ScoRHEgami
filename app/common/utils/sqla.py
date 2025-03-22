import asyncio
import dataclasses
import hashlib
import random
import time

from sqlalchemy import func as sa_func
from sqlalchemy import types as sa_types
from sqlalchemy.sql import expression as sa_exp

from app.common.ctx import AppCtx


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
        is_lock_obtained = (await AppCtx.current.db.execute(lock_query)).scalar()

        if is_lock_obtained:
            break

        if nowait:
            raise RuntimeError(f"the lock is not acquired at once (lock: {lock})")

        await asyncio.sleep(random.uniform(0.1, 0.2))

    else:
        raise RuntimeError(f"failed to obtain the advisory lock (lock: {lock})")
