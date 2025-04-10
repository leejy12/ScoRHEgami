from sqlalchemy import (
    Boolean,
    Column,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped

from .base_ import OrmBase


class Team(OrmBase):
    __tablename__ = "team"

    id: Mapped[int] = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    balldontlie_id: Mapped[int] = Column(
        Integer,
        nullable=True,
        unique=True,
        index=True,
    )
    short_name: Mapped[str | None] = Column(String, nullable=True)
    name: Mapped[str] = Column(String, unique=True, nullable=False)
    is_most_recent_name: Mapped[bool] = Column(Boolean, nullable=False)

    __table_args__ = (
        Index(
            "ix_unique_most_recent_name",
            balldontlie_id,
            is_most_recent_name,
            postgresql_where=(is_most_recent_name.is_(True)),
        ),
    )
