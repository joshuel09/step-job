"""Worker entrypoint and schedule.

Run the actors with:   uv run dramatiq app.main
Run the scheduler with: uv run python -m app.main

They are separate processes on purpose: the scheduler only enqueues, so a
scheduler restart never interrupts work already in flight.
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from .purge import purge_expired_profiles
from .settings import get_worker_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

# Imported for dramatiq's CLI to discover; referenced so linters keep it.
__all__ = ["purge_expired_profiles"]


def main() -> None:
    settings = get_worker_settings()
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        purge_expired_profiles.send,
        "interval",
        seconds=settings.purge_interval_seconds,
        id="purge-expired-profiles",
        # If the process was down over several intervals, run once on return
        # rather than firing the backlog.
        coalesce=True,
        max_instances=1,
    )

    logger.info("scheduler started; purge runs every %ss", settings.purge_interval_seconds)
    scheduler.start()


if __name__ == "__main__":
    main()
