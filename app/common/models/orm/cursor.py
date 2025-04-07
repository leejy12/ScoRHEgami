import datetime

from sqlalchemy import (
    TIMESTAMP,
    Column,
)
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Mapped


from .base_ import OrmBase

class Cursor(OrmBase):
    __tablename__ = "cursor"

    date: Mapped[datetime.datetime] = Column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        server_default=sa_func.now(),
    )

