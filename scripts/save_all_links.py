import scripts.baseball_reference as bref
import time


def main():
    first_season = 1901
    last_season = 2024
    for season in range(first_season, last_season + 1):
        urls = bref.get_links_of_season(season)
        urls_text = "\n".join(urls)

        with open(f"links/{season}.txt", "w") as f:
            f.write(urls_text)

        time.sleep(5)


if __name__ == "__main__":
    main()
