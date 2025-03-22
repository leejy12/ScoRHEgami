from .game import router as game_router
from .team import router as team_router

API_ROUTES = [
    game_router,
    team_router,
]
