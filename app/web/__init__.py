from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


from app.common.ctx import bind_app_ctx, create_app_ctx
from app.common.settings import AppSettings

from .team import router as team_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = AppSettings()

    app.extra["_app_ctx"] = await create_app_ctx(app_settings)

    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.include_router(team_router)

    async def app_ctx_middleware(request: Request, call_next):
        app_ctx = request.app.extra["_app_ctx"]
        async with bind_app_ctx(app_ctx):
            response = await call_next(request)
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=app_ctx_middleware)

    return app
