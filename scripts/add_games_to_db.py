import datetime
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import expression as sa_exp

import app.baseball_reference as bref
from app.common.ctx import AppCtx
from app.common.models import orm as m


def get_team_id(name: str):
    team = AppCtx.current.db.execute(
        sa_exp.select(m.Team).where(m.Team.name == name)
    ).scalar_one_or_none()

    if team is None:
        team = m.Team(short_name=None, name=name)
        AppCtx.current.db.add(team)
        AppCtx.current.db.commit()

    return team.id


def is_rhe_scorhegami(rhe: list[int]):
    rhe_exists = (
        AppCtx.current.db.scalar(
            sa_exp.select(sa_exp.exists().where(m.Game.rhe == rhe))
        )
        or False
    )

    return not rhe_exists


def main():
    for season in range(1901, 2025):
        results: list[str] = []
        with open(f"results/{season}.txt") as f:
            results = [result.strip() for result in f.readlines()]

        for result in results:
            game = bref.Game(**json.loads(result))

            away_team_id = get_team_id(game.away_team.name)
            home_team_id = get_team_id(game.home_team.name)

            is_scorhegami = is_rhe_scorhegami(game.rhe)
            new_game = m.Game(
                away_id=away_team_id,
                home_id=home_team_id,
                start_time=game.start_time,
                end_time=None,
                box_score=game.box_score,
                rhe=game.rhe,
                is_scorhegami=is_scorhegami,
            )

            while True:
                try:
                    AppCtx.current.db.add(new_game)
                    AppCtx.current.db.commit()
                    break
                except IntegrityError:
                    AppCtx.current.db.rollback()
                    new_game.start_time += datetime.timedelta(minutes=1)

            print(f"Added game: {game.start_time} {new_game.id}")

            if is_scorhegami:
                AppCtx.current.db.add(m.ScorhegamiGame(game_id=new_game.id))
                print("That game was a ScoRHEgami!\n")

            AppCtx.current.db.commit()


if __name__ == "__main__":
    main()
