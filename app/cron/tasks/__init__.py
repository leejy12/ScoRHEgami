from .game_fetcher import GameFetcherTask
from .game_updater import GameUpdaterTask
from .scorhegami_updater import ScorhegamiUpdaterTask

TASK_CLS_LIST = [
    GameFetcherTask,
    GameUpdaterTask,
    ScorhegamiUpdaterTask,
]
