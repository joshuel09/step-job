"""Running an import that was too slow to finish in the request.

Reaches the same outcomes as an in-request import, by calling the same code.
Being slow must not change what is produced, and must not relax the rule that a
failure creates no proposals (FR-005c, FR-017).

The source text arrives as an argument rather than from a table. Storing it
would mean a copy of someone's resume waiting in the queue's database, which is
exactly what the rest of this feature avoids.
"""

import logging
import uuid

import dramatiq
from app.career.models import CareerProfile
from app.db.session import SessionFactory
from app.imports.models import FailureReason, Import, ImportStatus
from sqlalchemy import select

from .purge import broker  # noqa: F401 - configures the shared broker

logger = logging.getLogger(__name__)


# The name here is the contract with app.imports.queue.EXTRACTION_ACTOR.
@dramatiq.actor(
    actor_name="extract_import",
    queue_name="default",
    max_retries=2,
    min_backoff=30_000,
)
def extract_import(profile_id: str, import_id: str, source: str) -> None:
    from app.imports import service

    session = SessionFactory()
    try:
        profile = session.scalars(
            select(CareerProfile).where(CareerProfile.id == uuid.UUID(profile_id))
        ).first()
        record = session.scalars(
            select(Import).where(Import.id == uuid.UUID(import_id))
        ).first()

        if profile is None or record is None:
            # The profile was deleted while the import was queued. Nothing to
            # do, and nothing to complain about.
            logger.info("import no longer exists", extra={"outcome": "skipped"})
            return

        if record.is_terminal:
            # Already finished or cancelled while queued. Re-running would
            # create a second set of proposals from one import.
            logger.info("import already settled", extra={"outcome": "skipped"})
            return

        service.run(session, profile, record, source)
        session.commit()

    except Exception:
        session.rollback()
        _mark_failed(import_id)
        logger.exception("background import failed")
        raise
    finally:
        session.close()


def _mark_failed(import_id: str) -> None:
    """Leave the import in a terminal state even when the run itself failed.

    Without this an import handed to the worker could sit at `running` for ever
    if the actor died, and SC-007 promises every import reaches an outcome.
    """
    session = SessionFactory()
    try:
        record = session.scalars(
            select(Import).where(Import.id == uuid.UUID(import_id))
        ).first()
        if record is not None and not record.is_terminal:
            record.status = ImportStatus.failed
            record.failure_reason = FailureReason.extraction_failed
            record.outcome = {
                "found": {},
                "not_found": [],
                "message": "Something went wrong reading that. Please try again.",
            }
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
