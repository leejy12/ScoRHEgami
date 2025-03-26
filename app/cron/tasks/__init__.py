from .game_fetcher import GameFetcherTask
from .game_updater import GameUpdaterTask

TASK_CLS_LIST = [
    GameFetcherTask,
    GameUpdaterTask,
]
