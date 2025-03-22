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
from sqlalchemy.orm import Mapped, declarative_base, relationship

Base = declarative_base()


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    short_name: Mapped[str | None] = Column(String, unique=True, nullable=True)
    name: Mapped[str] = Column(String, unique=True, nullable=False)


class Game(Base):
    __tablename__ = "game"

    id: Mapped[int] = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    away_id: Mapped[int] = Column(Integer, ForeignKey("team.id"), nullable=False)
    home_id: Mapped[int] = Column(Integer, ForeignKey("team.id"), nullable=False)

    away_team: Mapped[Team] = relationship("Team", foreign_keys=[away_id])
    home_team: Mapped[Team] = relationship("Team", foreign_keys=[home_id])

    start_time: Mapped[datetime.datetime | None] = Column(TIMESTAMP, nullable=True)
    end_time: Mapped[datetime.datetime | None] = Column(TIMESTAMP, nullable=True)

    box_score: Mapped[list[int]] = Column(ARRAY(Integer), nullable=False)
    rhe: Mapped[list[int]] = Column(ARRAY(Integer), nullable=False)
    is_scorhegami: Mapped[bool] = Column(Boolean, nullable=False)

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


class ScorhegamiGame(Base):
    __tablename__ = "scorhegami_game"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    game_id = Column(Integer, ForeignKey("game.id"), nullable=False)
