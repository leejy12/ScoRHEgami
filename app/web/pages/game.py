from ..config import templates

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

game_page_router = APIRouter(prefix="/game")


@game_page_router.get("", response_class=HTMLResponse)
async def _(request: Request):
    return templates.TemplateResponse(request, "game_list.html")
