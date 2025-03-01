import time

from sqlalchemy.sql import expression as sa_exp

import ScoRHEgami.baseball_reference as bref
from ScoRHEgami.common.ctx import AppCtx
from ScoRHEgami.common.models import orm as m


def get_team_id(team: bref.Team):
    team_id = AppCtx.current.db.execute(
        sa_exp.select(m.Team.id).where(m.Team.name == team.name)
    ).scalar_one_or_none()

    if team_id is None:
        new_team = m.Team(
            name=team.name,
            short_name=team.short_name,
        )
        AppCtx.current.db.add(new_team)
        AppCtx.current.db.flush()
        return new_team.id
    else:
        return team_id


def main():
    season = 1901

    links: list[str] = []
    with open(f"links/{season}.txt") as f:
        links = [link.strip() for link in f.readlines()]

    for link in links[:5]:
        print(f"Recording game link = {link}")
        game = bref.get_game_result(link)

        away_team_id = get_team_id(game.away_team)
        home_team_id = get_team_id(game.home_team)

        new_game = m.Game(
            away_id=away_team_id,
            home_id=home_team_id,
            start_time=None,
            box_score=game.box_score,
            rhe=game.rhe,
        )

        AppCtx.current.db.add(new_game)
        AppCtx.current.db.commit()
        print(f"Added game: {new_game.id}")

        time.sleep(5)


if __name__ == "__main__":
    main()
