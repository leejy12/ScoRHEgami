from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped

from app.common.models.app import TweetStatusEnum

from .base_ import OrmBase


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
    status: Mapped[TweetStatusEnum] = Column(String, nullable=False)
