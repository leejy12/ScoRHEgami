import ScoRHEgami.baseball_reference as bref
import time


def main():
    first_season = 1906
    last_season = 2024
    for season in range(first_season, last_season + 1):
        with open(f"links/{season}.txt", "r") as f:
            with open(f"results/{season}.txt", "a") as result_file:
                urls = [url.strip() for url in f.readlines()]
                for url in urls:
                    while True:
                        try:
                            result = bref.get_game_result(url)
                            result_file.write(f"{result.model_dump_json()}\n")
                            print(f"SUCCESS: {url}")
                            time.sleep(5)
                            break
                        except RuntimeError as e:
                            print(e)
                            time.sleep(5)
                            continue


if __name__ == "__main__":
    main()
