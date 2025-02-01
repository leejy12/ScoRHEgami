import ScoRHEgami.baseball_reference as bref


def main():
    season = int(input("Enter season: "))
    urls = bref.get_links_of_season(season)

    for url in urls:
        print(url)

    # cnt = 0

    # for url in urls:
    #     while cnt < 10:
    #         time.sleep(10)
    #         print(f"Getting game: {url}")
    #         game: bref.Game = bref.get_game_result(url)

    #         if game is not None:
    #             print(game)

    #             away_team_id: int = db.get_team_id_by_name(
    #                 game.away_team.short_name, game.away_team.full_name
    #             )
    #             home_team_id: int = db.get_team_id_by_name(
    #                 game.home_team.short_name, game.home_team.full_name
    #             )

    #             n = len(game.box_score)
    #             rhe: list[int] = (
    #                 game.box_score[n // 2 - 3 : n // 2] + game.box_score[n - 3 :]
    #             )

    #             db.insert_game(
    #                 away_id=away_team_id,
    #                 home_id=home_team_id,
    #                 start_time=game.start_time,
    #                 box_score=game.box_score,
    #                 rhe=rhe,
    #             )
    #             cnt += 1

    #             break

    # db.close()


if __name__ == "__main__":
    main()
