from sqlalchemy import (
    CheckConstraint,
    Index,
    Column,
    Integer,
    String,
    ARRAY,
    TIMESTAMP,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Team(Base):
    __tablename__ = "team"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    short_name = Column(String, unique=True, nullable=True)
    name = Column(String, unique=True, nullable=False)


class Game(Base):
    __tablename__ = "game"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    away_id = Column(Integer, ForeignKey("team.id"), nullable=False)
    home_id = Column(Integer, ForeignKey("team.id"), nullable=False)
    start_time = Column(TIMESTAMP, nullable=True)
    end_time = Column(TIMESTAMP, nullable=True)
    box_score = Column(ARRAY(Integer), nullable=False)
    rhe = Column(ARRAY(Integer), nullable=False)
    is_scorhegami = Column(Boolean, nullable=False)

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
