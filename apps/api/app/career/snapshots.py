"""Capturing what a generated document drew on.

Principle IV requires every AI-generated claim be traceable to the entries that
support it. Entries stay directly editable with no revision history (FR-030), so
a user rewriting a role after generating a resume would otherwise break that
trace — the document would cite wording that no longer exists.

A snapshot closes that gap: at the moment of generation, the entries used are
copied verbatim into an insert-only row (FR-028). It stays readable and unchanged
after those entries are edited or deleted (FR-029), which is the whole point.

Most entries are copied whole. The Japan profile never is: it holds residence
and visa details the user may have disclosed one at a time, and a whole copy
would put every withheld field into the durable record of what was sent. It is
captured field by field, naming only what the document showed.
"""

import uuid
from collections.abc import Iterable, Mapping
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

# Entities that may only be captured field by field, never whole.
CAPTURABLE_BY_FIELD = (models.JapanProfile,)

# Copied with every projection, so the entry stays traceable to its live row.
_ALWAYS = ("id", "profile_id")


def _value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, models.Locale | models.EmploymentType):
        return str(value)
    return value


def _serialise(entry: Any, fields: Iterable[str] | None = None) -> dict[str, Any]:
    columns = [column.name for column in entry.__table__.columns]
    if fields is not None:
        named = list(fields)
        unknown = [f for f in named if f not in columns]
        if unknown:
            raise ValueError(f"{type(entry).__name__} has no field {', '.join(unknown)}")
        columns = [c for c in columns if c in _ALWAYS or c in named]

    out: dict[str, Any] = {"__entity__": type(entry).__name__}
    for name in columns:
        out[name] = _value(getattr(entry, name))
    return out


def capture(
    session: Session,
    profile: models.CareerProfile,
    document_ref: str,
    entry_ids: list[uuid.UUID],
    fields: Mapping[uuid.UUID, Iterable[str]] | None = None,
) -> models.EntrySnapshot:
    """Copy the named entries as they read right now.

    Every id must belong to the caller's profile: a snapshot that could capture
    someone else's entry would make the traceability record itself a leak.

    `fields` narrows an entry to the named fields. A Japan profile must be
    narrowed this way, by the caller that knows what the user disclosed, so
    no path through here stores a withheld field.
    """
    fields = fields or {}
    if not entry_ids:
        raise ValidationFailed([("entry_ids", "must name at least one entry")])

    found: dict[uuid.UUID, Any] = {}
    for model in CAPTURABLE + CAPTURABLE_BY_FIELD:
        for entry in session.scalars(
            select(model).where(model.id.in_(entry_ids), model.profile_id == profile.id)
        ):
            found[entry.id] = entry

    missing = [str(i) for i in entry_ids if i not in found]
    if missing:
        raise ValidationFailed(
            [("entry_ids", f"no such entry in this profile: {', '.join(missing)}")]
        )

    whole = [
        str(entry_id)
        for entry_id, entry in found.items()
        if isinstance(entry, CAPTURABLE_BY_FIELD) and entry_id not in fields
    ]
    if whole:
        raise ValidationFailed(
            [("entry_ids", f"can only be captured field by field: {', '.join(whole)}")]
        )

    snapshot = models.EntrySnapshot(
        profile_id=profile.id,
        document_ref=document_ref,
        captured_at=datetime.now(UTC),
        captured_entry_ids=list(found),
        payload={
            str(entry_id): _serialise(entry, fields.get(entry_id))
            for entry_id, entry in found.items()
        },
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
