import datetime

from sqlalchemy import (
    TIMESTAMP,
    Column,
)
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Mapped, declarative_base

Base = declarative_base()


class OrmBase(Base):
    __abstract__ = True

    created_at: Mapped[datetime.datetime] = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa_func.now(),
    )

    updated_at: Mapped[datetime.datetime] = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa_func.now(),
        onupdate=sa_func.now(),
    )
