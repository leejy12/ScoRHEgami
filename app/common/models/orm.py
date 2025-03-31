import datetime

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Mapped, declarative_base, relationship

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


class Cursor(OrmBase):
    __tablename__ = "cursor"

    date: Mapped[datetime.datetime] = Column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        server_default=sa_func.now(),
    )


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


class Game(OrmBase):
    __tablename__ = "game"

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

    away_id: Mapped[int] = Column(Integer, ForeignKey("team.id"), nullable=False)
    home_id: Mapped[int] = Column(Integer, ForeignKey("team.id"), nullable=False)

    away_team: Mapped[Team] = relationship("Team", foreign_keys=[away_id])
    home_team: Mapped[Team] = relationship("Team", foreign_keys=[home_id])

    start_time: Mapped[datetime.datetime | None] = Column(
        TIMESTAMP(timezone=True), nullable=True
    )
    end_time: Mapped[datetime.datetime | None] = Column(
        TIMESTAMP(timezone=True), nullable=True
    )

    box_score: Mapped[list[int]] = Column(ARRAY(Integer), nullable=True)
    rhe: Mapped[list[int]] = Column(ARRAY(Integer), nullable=True)
    status: Mapped[str] = Column(String, index=True, nullable=True)
    is_scorhegami: Mapped[bool] = Column(Boolean, nullable=True)

    bref_url: Mapped[str] = Column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_unique_game",
            "home_id",
            "away_id",
            "start_time",
            unique=True,
            postgresql_where=(start_time.isnot(None)),
        ),
        Index("ix_game_box_score", box_score, postgresql_using="gin"),
        Index("ix_game_rhe", rhe, postgresql_using="gin"),
        CheckConstraint("home_id != away_id", name="different_teams_constraint"),
    )


class Tweet(OrmBase):
    __tablename__ = "tweet"

    id: Mapped[int] = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    game_id: Mapped[int] = Column(
        Integer, ForeignKey("game.id"), nullable=False, index=True
    )

    tweet_id: Mapped[str | None] = Column(String, nullable=True)
    content: Mapped[str | None] = Column(String, nullable=True)

    tweet_failed_reason = Column(String, nullable=True)
