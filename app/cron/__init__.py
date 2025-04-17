from __future__ import annotations

import asyncio
import logging
import signal
import sys
import threading
from types import FrameType

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from app.common.ctx import create_app_ctx
from app.common.settings import AppSettings
from app.cron.tasks import TASK_CLS_LIST
from app.cron.tasks.base import AsyncComponent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(module)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class CronApp:
    def __init__(self, app_settings: AppSettings) -> None:
        self.app_settings = app_settings

        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        sentry_sdk.init(
            dsn=app_settings.SENTRY_DSN,
            integrations=[sentry_logging],
            traces_sample_rate=1.0,
        )

        self._terminate_event = threading.Event()

        def _handle_signal_exit(signum: int, _: FrameType | None) -> None:
            logger.info("Signal %s recieved.", signal.Signals(signum).name)

            if self._terminate_event.is_set():
                logger.info("Forceful exit.")
                sys.exit(1)
            else:
                self._terminate_event.set()

        signal.signal(signal.SIGTERM, _handle_signal_exit)
        signal.signal(signal.SIGINT, _handle_signal_exit)

    def run(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        app_ctx = await create_app_ctx(self.app_settings)

        try:
            started_components: list[AsyncComponent] = []
            for task_cls in TASK_CLS_LIST:
                task_instance = task_cls(app_ctx)
                await task_instance.start()

                logger.info("Start %s", task_cls.__name__)

                started_components.append(task_instance)

            while not self._terminate_event.is_set() and all(
                component.is_healthy() for component in started_components
            ):
                await asyncio.sleep(0.1)

        except Exception:
            logger.warning("exception from components", exc_info=True)

        finally:
            for component in reversed(started_components):
                try:
                    await component.stop()
                except Exception:
                    logger.warning(
                        "exception while stopping component : %s",
                        component.__class__.__name__,
                        exc_info=True,
                    )
