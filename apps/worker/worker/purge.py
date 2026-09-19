"""Permanently erasing profiles once their recovery window closes.

FR-025 gives a deleted profile exactly 30 days, after which everything remaining
must be erased without further action by the user. The immigration-related
fields were already destroyed on the request path (see the API's deletion module)
— this is the sweep for everything else.

Written to be idempotent (research.md R-002): re-running over an already-purged
profile is a no-op, so a retry after a partial failure cannot fail the batch, and
a scheduler that fires twice does no harm.
"""

import logging
from datetime import UTC, datetime

import dramatiq
from app.career.models import CareerProfile
from app.db.session import SessionFactory
from app.db.soft_delete import with_deleted
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select

from .settings import get_worker_settings

logger = logging.getLogger(__name__)

broker = RedisBroker(url=get_worker_settings().redis_url)
dramatiq.set_broker(broker)


def find_due(session, now: datetime | None = None) -> list[CareerProfile]:
    """Profiles whose recovery window has closed.

    Uses the deleted-visible escape hatch deliberately: ordinary reads exclude
    soft-deleted profiles, which is exactly the rows this job exists to find.
    """
    moment = now or datetime.now(UTC)
    with with_deleted(session):
        return list(
            session.scalars(
                select(CareerProfile).where(
                    CareerProfile.deleted_at.is_not(None),
                    CareerProfile.purge_after.is_not(None),
                    CareerProfile.purge_after <= moment,
                )
            )
        )


def purge_due_profiles(session, now: datetime | None = None) -> int:
    """Erase every profile past its purge date. Returns how many were erased.

    Deleting the profile row cascades to every section, career story, proposed
    entry and snapshot beneath it (FR-031), so nothing is left orphaned holding
    career data.
    """
    due = find_due(session, now)
    if not due:
        # Not an error, and the common case. Idempotency falls out of this:
        # a second run finds nothing because the first run's rows are gone.
        return 0

    for profile in due:
        logger.info(
            "purging profile",
            extra={"profile_id": str(profile.id), "outcome": "purged"},
        )
        session.delete(profile)

    session.flush()
    return len(due)


@dramatiq.actor(max_retries=3, min_backoff=60_000)
def purge_expired_profiles() -> None:
    session = SessionFactory()
    try:
        erased = purge_due_profiles(session)
        session.commit()
        if erased:
            logger.info("purge complete", extra={"profiles_erased": erased})
    except Exception:
        session.rollback()
        logger.exception("purge failed; it will be retried")
        raise
    finally:
        session.close()
