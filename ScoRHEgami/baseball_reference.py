import requests
import httpx
from bs4 import BeautifulSoup, Comment, Tag
from datetime import datetime
from pydantic import BaseModel

BREF_BASEURL = "https://www.baseball-reference.com"


class Team(BaseModel):
    short_name: str
    name: str


# Game result
# let N = len(box_score). N is even.
# box_score[: N // 2 - 3]        = Runs scored by away team.
# box_score[N // 2 - 3 : N // 2] = RHE by away team.
# box_score[N // 2 : N - 3]      = Runs scored by home team.
# box_score[N - 3 :]             = RHE by home team.
class Game(BaseModel):
    away_team: Team
    home_team: Team
    start_time: datetime
    box_score: list[int]

    def __str__(self):
        s: str = ""
        s += f"{self.away_team} vs {self.home_team} ({self.start_time})\n"
        s += f"{self.box_score[: len(self.box_score) // 2]}\n"
        s += f"{self.box_score[len(self.box_score) // 2 :]}\n"
        return s

    @property
    def rhe(self):
        N = len(self.box_score)
        return self.box_score[N // 2 - 3 : N // 2] + self.box_score[N - 3 :]


def get_links_of_season(year: int) -> list[str]:
    url = f"{BREF_BASEURL}/leagues/majors/{year}-schedule.shtml"
    response: requests.Response = requests.get(url)

    if response.status_code != 200:
        raise RuntimeError(f"Failed with response: {response.status_code}")

    soup = BeautifulSoup(response.content, "lxml")

    main_sections: list[Tag] = soup.find_all("div", class_="section_content")[:2]

    urls = []

    # First section is for regular season.
    # Second section (if it exists) is for postseason.
    for section in main_sections:
        # Get links to _Boxscore_.
        a_tags: list[Tag] = section.find_all(
            "a",
            href=lambda href: isinstance(href, str)
            and href.startswith("/boxes/")
            and href.endswith(".shtml"),
        )
        urls.extend([f"{BREF_BASEURL}{a_tag.get('href')}" for a_tag in a_tags])

    return urls


def get_game_result(url: str) -> Game:
    response = httpx.get(url)

    if response.status_code != 200:
        raise RuntimeError(f"Failed with response: {response.status_code}")

    # `url` is like "...YYYYMMDDX.shtml". X is for counting double-headers.
    yyyymmdd: str = url[-15:-7]
    start_time: datetime = datetime.strptime(yyyymmdd, "%Y%m%d")

    soup = BeautifulSoup(response.content, "lxml")

    # For some reason, the game summary section is commented out in the response body.
    # Parse the comment again with BeautifulSoup.
    teams_short: list[str] = []
    current_game_summary = None
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if "game_summaries compressed" in comment:
            game_summary_soup = BeautifulSoup(comment, "lxml")
            current_game_summary = game_summary_soup.find(
                "div", class_="game_summary nohover current"
            )
            break

    if current_game_summary is None:
        current_game_summary = soup.find("div", class_="game_summary nohover current")

    for a in current_game_summary.find_all(  # type: ignore
        "a",
        href=lambda href: isinstance(href, str) and href.startswith("/teams/"),
    ):
        teams_short.append(a.get_text())

    away_team_short: str = teams_short[0]
    home_team_short: str = teams_short[1]

    box_score = soup.find("table", class_="linescore nohover stats_table no_freeze")
    if not box_score:
        return

    teams: list[str] = []

    for a in box_score.find_all(  # type: ignore
        "a", href=lambda href: isinstance(href, str) and href.startswith("/teams/")
    ):
        teams.append(a.get_text())

    away_team_long: str = teams[0]
    home_team_long: str = teams[1]

    # Find <td class="center">1</td>. This is the number in box score.
    only_number_tds = [
        td
        for td in box_score.find_all("td", class_="center")  # type: ignore
        if not td.find_all()
    ]

    scores_rhe: list[int] = []

    for td in only_number_tds:
        score = td.get_text()

        n: int = 0 if score == "X" else int(score)
        scores_rhe.append(n)

    away_team = Team(short_name=away_team_short, name=away_team_long)
    home_team = Team(short_name=home_team_short, name=home_team_long)

    return Game(
        away_team=away_team,
        home_team=home_team,
        start_time=start_time,
        box_score=scores_rhe,
    )
