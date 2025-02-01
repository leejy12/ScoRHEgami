from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
    Column,
    Integer,
    String,
    ARRAY,
    TIMESTAMP,
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import declarative_base, Relationship
from sqlalchemy import func as sa_func

Base = declarative_base()


class Team(Base):
    __tablename__ = "team"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        index=True,
        server_default=sa_func.gen_random_uuid(),
    )
    short_name = Column(String, unique=True)
    name = Column(String, unique=True)


class Game(Base):
    __tablename__ = "game"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        index=True,
        default=sa_func.gen_random_uuid(),
    )
    away_id = Column(Uuid(as_uuid=True), ForeignKey("team.id"))
    home_id = Column(Uuid(as_uuid=True), ForeignKey("team.id"))
    start_time = Column(TIMESTAMP)
    box_score = Column(ARRAY(Integer))
    rhe = Column(ARRAY(Integer))

    home_team = Relationship(
        "Team", foreign_keys=[home_id], back_populates="home_games"
    )

    away_team = Relationship(
        "Team", foreign_keys=[away_id], back_populates="away_games"
    )

    __table_args__ = (
        UniqueConstraint(
            "home_id", "away_id", "start_time", name="unique_game_constraint"
        ),
        CheckConstraint("home_id != away_id", name="different_teams_constraint"),
    )
