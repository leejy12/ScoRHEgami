from __future__ import annotations

from app.common.settings import AppSettings
from app.cron import CronApp

app_settings = AppSettings()


worker = CronApp(app_settings)

if __name__ == "__main__":
    import uvloop

    uvloop.install()

    worker.run()
