from fastapi.routing import APIRouter

from .game import router as game_router
from .team import router as team_router

api_router = APIRouter(prefix="/api")

api_router.include_router(game_router)
api_router.include_router(team_router)
