"""Approving, listing and removing a stored English version.

Three things happen here and one deliberately does not.

**Approving** writes the user's words exactly as they gave them, together
with a digest of the source as it read at that moment. The digest is the
only reason staleness is detectable later (FR-023), and it is taken from
the entry rather than from anything the caller sent: a client that posted
its own idea of the source could otherwise record an approval as matching
text the profile never held.

**Listing** compares each stored digest against the source as it reads now.
A changed source does not discard the approval and does not re-draft it —
the user approved those words, and a typo fix in the Japanese does not
withdraw that. They are told, and the document still carries their English.

**Removing** takes an entry's renderings when the entry goes. FR-024 allows
no stored English to outlive the entry it is a translation of, and
`entry_id` cannot be a foreign key — it points at one of four tables
depending on `entry_type` — so nothing in the database enforces it. This
module is the enforcement, and the tests in
`tests/integration/test_translation_flow.py` are the foreign key.

**No model is reached from here.** Drafting lives in `drafting.py` for one
reason: `app/resume/` reads this module for its readiness report, and
`tests/unit/test_ai_boundary.py` fails the build if anything under
`app/resume/` can reach `app.ai` transitively. Keeping the provider out of
this file is what lets the boundary hold without the readiness report
having to re-implement staleness.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.career.models import Locale
from app.core.errors import NotFoundError
from app.translations import entries, schemas
from app.translations.fingerprint import fingerprint, is_stale
from app.translations.models import EntryTranslation, TranslatableEntry

logger = logging.getLogger(__name__)


def delete_for_entry(
    session: Session,
    profile_id: uuid.UUID,
    entry_type: TranslatableEntry,
    entry_id: uuid.UUID,
) -> int:
    """Remove every rendering stored against one entry. Returns how many.

    Scoped by profile as well as by entry, so a `entry_id` that collided
    across profiles could not reach another user's rows. Returning the
    count rather than nothing is what lets the caller log a deletion that
    took English with it.
    """
    removed = session.execute(
        delete(EntryTranslation).where(
            EntryTranslation.profile_id == profile_id,
            EntryTranslation.entry_type == entry_type,
            EntryTranslation.entry_id == entry_id,
        )
    ).rowcount

    if removed:
        logger.info(
            "translations deleted with their entry",
            extra={
                "profile_id": profile_id,
                "entry_id": entry_id,
                "entry_type": entry_type.value,
                "count": removed,
            },
        )
    return removed


def approve(
    session: Session,
    profile_id: uuid.UUID,
    approval: schemas.TranslationApproval,
    *,
    language: Locale = Locale.en,
) -> EntryTranslation:
    """Store the user's English for one field, replacing any before it.

    An upsert on the natural key rather than an insert, because the unique
    constraint says there is one approved version per field and a second
    row would make "the approved text" a question. Approving again is how
    a user corrects their own wording, and it must not be an error.

    The entry is read first, so an id that is not on this profile is a 404
    and the fingerprint is of text this profile actually holds.
    """
    entry = entries.require(session, profile_id, approval.entry_type, approval.entry_id)
    entries.require_field(approval.entry_type, approval.field)
    source = entries.source_text(entry, approval.field)

    stored = _find(
        session,
        profile_id,
        approval.entry_type,
        approval.entry_id,
        approval.field,
        language=language,
    )
    if stored is None:
        stored = EntryTranslation(
            profile_id=profile_id,
            entry_type=approval.entry_type,
            entry_id=approval.entry_id,
            field=approval.field,
            language=language,
        )
        session.add(stored)

    stored.approved_text = approval.text
    stored.approved_at = datetime.now(UTC)
    stored.source_fingerprint = fingerprint(source)
    session.flush()

    # What was approved is not logged. The approved text is the user's
    # career in their own words, and a log line is the one place in this
    # system it would sit unencrypted and un-deletable.
    logger.info(
        "translation approved",
        extra={
            "profile_id": profile_id,
            "entry_id": approval.entry_id,
            "entry_type": approval.entry_type.value,
            "outcome": approval.field,
        },
    )
    return stored


def remove(session: Session, profile_id: uuid.UUID, translation_id: uuid.UUID) -> None:
    """Delete one stored version, or 404 if this profile has no such row."""
    stored = session.scalars(
        select(EntryTranslation).where(
            EntryTranslation.profile_id == profile_id,
            EntryTranslation.id == translation_id,
        )
    ).first()
    if stored is None:
        raise NotFoundError("No such stored English version on this profile.")

    session.delete(stored)
    session.flush()
    logger.info(
        "translation removed",
        extra={
            "profile_id": profile_id,
            "entry_id": stored.entry_id,
            "entry_type": stored.entry_type.value,
        },
    )


def stored_for_profile(
    session: Session,
    profile_id: uuid.UUID,
    *,
    language: Locale = Locale.en,
    stale: bool | None = None,
) -> list[schemas.StoredTranslation]:
    """Every approved version this profile holds, with staleness resolved.

    `stale=None` returns all of them. The filter is applied after the
    comparison rather than in the query, because staleness is not a column
    — it is what two values say when put beside each other, and storing it
    would mean a row that went stale when the entry was edited elsewhere.
    """
    rows = session.scalars(
        select(EntryTranslation)
        .where(
            EntryTranslation.profile_id == profile_id,
            EntryTranslation.language == language,
        )
        .order_by(EntryTranslation.approved_at.desc())
    )

    reported = [report(session, profile_id, row) for row in rows]
    if stale is None:
        return reported
    return [item for item in reported if item.is_stale is stale]


def report(
    session: Session, profile_id: uuid.UUID, row: EntryTranslation
) -> schemas.StoredTranslation:
    """One stored version, said as the contract says it.

    A row whose entry cannot be found is reported stale with no source.
    That row should not exist — deleting an entry takes its renderings
    (FR-024) — and if one ever does, the honest thing to tell the user is
    that the approval no longer describes anything, not to fail the whole
    report over it.
    """
    entry = entries.find(session, profile_id, row.entry_type, row.entry_id)
    if entry is None:
        logger.warning(
            "stored translation has no entry",
            extra={
                "profile_id": profile_id,
                "entry_id": row.entry_id,
                "entry_type": row.entry_type.value,
            },
        )
        return schemas.StoredTranslation(
            id=row.id,
            entry_type=row.entry_type,
            entry_id=row.entry_id,
            field=row.field,
            text=row.approved_text,
            approved_at=row.approved_at,
            is_stale=True,
        )

    source = entries.source_text(entry, row.field)
    stale = is_stale(row.source_fingerprint, source)
    return schemas.StoredTranslation(
        id=row.id,
        entry_type=row.entry_type,
        entry_id=row.entry_id,
        field=row.field,
        text=row.approved_text,
        approved_at=row.approved_at,
        is_stale=stale,
        source_text=source if stale else None,
    )


def _find(
    session: Session,
    profile_id: uuid.UUID,
    entry_type: TranslatableEntry,
    entry_id: uuid.UUID,
    field: str,
    *,
    language: Locale,
) -> EntryTranslation | None:
    return session.scalars(
        select(EntryTranslation).where(
            EntryTranslation.profile_id == profile_id,
            EntryTranslation.entry_type == entry_type,
            EntryTranslation.entry_id == entry_id,
            EntryTranslation.field == field,
            EntryTranslation.language == language,
        )
    ).first()
