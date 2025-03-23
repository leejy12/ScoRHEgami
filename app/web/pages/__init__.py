from fastapi import APIRouter

from .game import game_page_router

page_router = APIRouter()

page_router.include_router(game_page_router)
