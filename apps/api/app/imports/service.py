"""The import lifecycle.

An import always reaches a terminal state (SC-007). It either produces proposals
or says why it could not, and a failure produces nothing at all — a partial set
is indistinguishable from a complete one, which would leave a user believing
their document held less than it did (FR-017).

Proposals are written to the review queue and nowhere else. Nothing extracted
reaches a profile except by the user accepting it.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import get_provider
from app.ai.provider import (
    AIProvider,
    NoExtractableContent,
    ProviderResponseInvalid,
    ProviderUnavailable,
)
from app.career import models as career_models
from app.career import proposals
from app.core.errors import ConflictError, NotFoundError
from app.core.settings import get_settings
from app.imports import extraction
from app.imports.models import FailureReason, Import, ImportStatus, SourceKind

logger = logging.getLogger(__name__)


def create(
    session: Session, profile: career_models.CareerProfile, source_kind: SourceKind
) -> Import:
    record = Import(
        profile_id=profile.id,
        source_kind=source_kind,
        status=ImportStatus.pending,
        started_at=datetime.now(UTC),
    )
    session.add(record)
    session.flush()
    return record


def get(session: Session, profile: career_models.CareerProfile, import_id: uuid.UUID) -> Import:
    record = session.scalars(
        select(Import).where(Import.id == import_id, Import.profile_id == profile.id)
    ).first()
    if record is None:
        raise NotFoundError("No such import in this profile.")
    return record


def list_for(
    session: Session,
    profile: career_models.CareerProfile,
    status: ImportStatus | None = None,
) -> list[Import]:
    statement = select(Import).where(Import.profile_id == profile.id)
    if status is not None:
        statement = statement.where(Import.status == status)
    return list(session.scalars(statement.order_by(Import.started_at.desc())))


def fail(session: Session, record: Import, reason: FailureReason, message: str) -> Import:
    """End an import having produced nothing.

    Nothing to clean up: proposals are only written once extraction has fully
    succeeded, so a failure has nothing to undo (FR-017d).
    """
    record.status = ImportStatus.failed
    record.failure_reason = reason
    record.completed_at = datetime.now(UTC)
    record.outcome = {"found": {}, "not_found": [], "message": message}
    session.flush()

    logger.info(
        "import failed",
        extra={"profile_id": record.profile_id, "outcome": str(reason)},
    )
    return record


def cancel(session: Session, profile: career_models.CareerProfile, import_id: uuid.UUID) -> Import:
    """Abandon an import before its proposals reach review (FR-018)."""
    record = get(session, profile, import_id)
    if record.is_terminal:
        raise ConflictError("This import has already finished.")

    record.status = ImportStatus.failed
    record.failure_reason = FailureReason.extraction_failed
    record.completed_at = datetime.now(UTC)
    record.outcome = {"found": {}, "not_found": [], "message": "Cancelled."}
    session.flush()
    return record


def run(
    session: Session,
    profile: career_models.CareerProfile,
    record: Import,
    source: str,
    provider: AIProvider | None = None,
) -> Import:
    """Extract from the source and create proposals, or fail saying why.

    Retries are bounded. A brief outage should not cost a user their import, and
    a persistent one must not leave them waiting on a recovery that may never
    come (FR-017a, FR-017c).
    """
    settings = get_settings()
    provider = provider or get_provider()

    record.status = ImportStatus.running
    session.flush()

    attempts = max(1, settings.ai_max_retries)
    last_unavailable: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            outcome = extraction.extract(provider, source)
            break
        except ProviderUnavailable as error:
            last_unavailable = error
            logger.info(
                "provider unavailable, retrying",
                extra={"count": attempt, "outcome": "retry"},
            )
        except ProviderResponseInvalid:
            return fail(
                session,
                record,
                FailureReason.extraction_failed,
                "We could not read what the extraction service returned. Please try again.",
            )
        except NoExtractableContent:
            return fail(
                session,
                record,
                FailureReason.no_career_information,
                "We read the document but found no career information in it.",
            )
    else:
        # Every attempt hit an outage. Said plainly, and distinguished from a
        # document that cannot be read — one is worth returning to, the other
        # never will be (FR-017b).
        logger.info("provider unavailable, giving up", extra={"outcome": "unavailable"})
        return fail(
            session,
            record,
            FailureReason.service_unavailable,
            "The extraction service is unavailable. Your document was not used. "
            "Please try again later.",
            )

    if last_unavailable is not None:
        logger.info("recovered after retry", extra={"outcome": "recovered"})

    if not outcome.entries:
        return fail(
            session,
            record,
            FailureReason.no_career_information,
            "We read the document but found no career information we could verify.",
        )

    created = _create_proposals(session, profile, record, outcome)

    record.status = ImportStatus.completed
    record.completed_at = datetime.now(UTC)
    record.entry_count = len(created)
    record.outcome = _describe(outcome, created)
    session.flush()

    logger.info(
        "import completed",
        extra={"profile_id": profile.id, "count": len(created), "outcome": "completed"},
    )
    return record


def _create_proposals(
    session: Session,
    profile: career_models.CareerProfile,
    record: Import,
    outcome: extraction.ExtractionOutcome,
) -> list[career_models.ProposedEntry]:
    """Write verified entries into the review queue, and nowhere else."""
    items = [
        {
            "entry_type": str(entry.entry_type),
            "source": f"import:{record.source_kind}",
            "payload": entry.values,
        }
        for entry in outcome.entries
    ]

    created = proposals.submit(session, profile, items)

    # Evidence and conflicts belong to the proposal they justify.
    for proposal, entry in zip(created, outcome.entries, strict=True):
        proposal.import_id = record.id
        proposal.evidence = entry.evidence
        proposal.conflicts = entry.conflicts or None

    session.flush()
    return created


def _describe(
    outcome: extraction.ExtractionOutcome, created: list[career_models.ProposedEntry]
) -> dict[str, Any]:
    found: dict[str, int] = {}
    for proposal in created:
        found[str(proposal.entry_type)] = found.get(str(proposal.entry_type), 0) + 1

    message = f"Found {len(created)} entries you can review."
    if outcome.dropped_fields or outcome.dropped_entries:
        # Said out loud rather than hidden: a user should know the document was
        # read conservatively, not assume something was lost.
        message += (
            f" {outcome.dropped_fields} values were left out because the document "
            "did not support them."
        )

    return {"found": found, "not_found": outcome.not_found, "message": message}
