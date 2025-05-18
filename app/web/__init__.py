from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import sentry_sdk

from app.common.ctx import bind_app_ctx, create_app_ctx
from app.common.settings import AppSettings

from .apis import API_ROUTERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = AppSettings()

    app.extra["_app_ctx"] = await create_app_ctx(app_settings)

    sentry_sdk.init(
        dsn=app_settings.SENTRY_DSN,
        send_default_pii=True,
    )

    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    for api_router in API_ROUTERS:
        app.include_router(api_router)

    async def app_ctx_middleware(request: Request, call_next):
        app_ctx = request.app.extra["_app_ctx"]
        async with bind_app_ctx(app_ctx):
            response = await call_next(request)
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=app_ctx_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://mlbscorhegami.com",
            "https://delightful-sky-03e70370f.6.azurestaticapps.net",
        ],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    return app
