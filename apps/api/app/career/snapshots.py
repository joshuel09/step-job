"""Capturing what a generated document drew on.

Principle IV requires every AI-generated claim be traceable to the entries that
support it. Entries stay directly editable with no revision history (FR-030), so
a user rewriting a role after generating a resume would otherwise break that
trace — the document would cite wording that no longer exists.

A snapshot closes that gap: at the moment of generation, the entries used are
copied verbatim into an insert-only row (FR-028). It stays readable and unchanged
after those entries are edited or deleted (FR-029), which is the whole point.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career import models
from app.core.errors import NotFoundError, ValidationFailed

# Every entity a document may legitimately draw on.
CAPTURABLE = (
    models.WorkExperience,
    models.Education,
    models.Certification,
    models.Skill,
    models.Language,
    models.CareerStory,
    models.Identity,
    models.CareerPreference,
)


def _serialise(entry: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"__entity__": type(entry).__name__}
    for column in entry.__table__.columns:
        value = getattr(entry, column.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, models.Locale | models.EmploymentType):
            value = str(value)
        out[column.name] = value
    return out


def capture(
    session: Session,
    profile: models.CareerProfile,
    document_ref: str,
    entry_ids: list[uuid.UUID],
) -> models.EntrySnapshot:
    """Copy the named entries as they read right now.

    Every id must belong to the caller's profile: a snapshot that could capture
    someone else's entry would make the traceability record itself a leak.
    """
    if not entry_ids:
        raise ValidationFailed([("entry_ids", "must name at least one entry")])

    found: dict[uuid.UUID, Any] = {}
    for model in CAPTURABLE:
        for entry in session.scalars(
            select(model).where(model.id.in_(entry_ids), model.profile_id == profile.id)
        ):
            found[entry.id] = entry

    missing = [str(i) for i in entry_ids if i not in found]
    if missing:
        raise ValidationFailed(
            [("entry_ids", f"no such entry in this profile: {', '.join(missing)}")]
        )

    snapshot = models.EntrySnapshot(
        profile_id=profile.id,
        document_ref=document_ref,
        captured_at=datetime.now(UTC),
        captured_entry_ids=list(found),
        payload={str(entry_id): _serialise(entry) for entry_id, entry in found.items()},
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def read(
    session: Session, profile: models.CareerProfile, snapshot_id: uuid.UUID
) -> models.EntrySnapshot:
    snapshot = session.scalars(
        select(models.EntrySnapshot).where(
            models.EntrySnapshot.id == snapshot_id,
            models.EntrySnapshot.profile_id == profile.id,
        )
    ).first()
    if snapshot is None:
        raise NotFoundError("No such snapshot in this profile.")
    return snapshot


__all__ = ["capture", "read"]
