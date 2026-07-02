import os

from app.jobs.scheduler import scheduler


def _job() -> None:
    from app.modules.football.service import sync_games
    sync_games()


def start() -> None:
    interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))
    scheduler.add_job(_job, "interval", minutes=interval, id="sync_games", replace_existing=True)
    if not scheduler.running:
        scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
