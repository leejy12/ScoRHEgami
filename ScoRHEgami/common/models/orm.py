from sqlalchemy import (
    CheckConstraint,
    Index,
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
    short_name = Column(String, unique=True, nullable=False)
    name = Column(String, unique=True, nullable=False)


class Game(Base):
    __tablename__ = "game"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        index=True,
        default=sa_func.gen_random_uuid(),
    )
    away_id = Column(Uuid(as_uuid=True), ForeignKey("team.id"), nullable=False)
    home_id = Column(Uuid(as_uuid=True), ForeignKey("team.id"), nullable=False)
    start_time = Column(TIMESTAMP)
    box_score = Column(ARRAY(Integer), nullable=False)
    rhe = Column(ARRAY(Integer), nullable=False)

    home_team = Relationship(
        "Team", foreign_keys=[home_id], back_populates="home_games"
    )

    away_team = Relationship(
        "Team", foreign_keys=[away_id], back_populates="away_games"
    )

    __table_args__ = (
        Index(
            "ix_unique_game",
            "home_id",
            "away_id",
            "start_time",
            unique=True,
            postgresql_where=(start_time.isnot(None)),
        ),
        CheckConstraint("home_id != away_id", name="different_teams_constraint"),
    )
