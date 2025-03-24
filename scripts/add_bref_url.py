import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import expression as sa_exp

from app.common.models import orm as m
from app.common.settings import AppSettings


async def main():
    session = async_sessionmaker(bind=create_async_engine(url=AppSettings().DB_URI))()

    id_ = 1
    for season in range(1901, 2025):
        with open(f"links/{season}.txt") as f:
            links = f.readlines()

            for link in links:
                link = link.strip()

                while True:
                    game_exists = (
                        await session.execute(
                            sa_exp.select(sa_exp.exists().where(m.Game.id == id_))
                        )
                    ).scalar() or False

                    if game_exists:
                        break
                    else:
                        id_ += 1

                await session.execute(
                    sa_exp.update(m.Game).values(bref_url=link).where(m.Game.id == id_)
                )

                id_ += 1

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
