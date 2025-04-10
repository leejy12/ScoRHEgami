import datetime

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Integer,
    String,
)
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Mapped

from app.common.models.app import CronTaskEnum

from .base_ import OrmBase


class Cursor(OrmBase):
    __tablename__ = "cursor"

    id: Mapped[int] = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    task_name: Mapped[CronTaskEnum] = Column(String, nullable=False)

    last_completed: Mapped[datetime.datetime] = Column(
        TIMESTAMP(timezone=True),
        server_default=sa_func.now(),
    )
