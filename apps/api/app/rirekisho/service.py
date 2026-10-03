"""Producing a 履歴書.

Gathers what the profile holds, projects the table, captures a snapshot of the
entries used, and renders. The snapshot and the render happen in one
transaction, so a render that fails leaves no record of a document that never
existed (research.md R-003).

This is the first consumer of the snapshot machinery feature 001 built. Until
now nothing has called it.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career import models as career_models
from app.career import snapshots
from app.core.errors import ValidationFailed
from app.rirekisho import render
from app.rirekisho.rows import build_rows
from app.rirekisho.schemas import DateConvention, PaperSize

logger = logging.getLogger(__name__)

# Without these a document is not a 履歴書, so generation refuses rather than
# producing one with a blank where a name belongs (FR-015).
REQUIRED = ("full_name_latin",)


def _section(session: Session, profile: career_models.CareerProfile, model: type) -> list[Any]:
    return list(session.scalars(select(model).where(model.profile_id == profile.id)))


def _identity(session: Session, profile: career_models.CareerProfile):
    return session.scalars(
        select(career_models.Identity).where(career_models.Identity.profile_id == profile.id)
    ).first()


def _require_identity(identity) -> None:
    if identity is None:
        raise ValidationFailed(
            [("identity", "add your name before generating a 履歴書")],
            "A 履歴書 cannot be produced without a name.",
        )

    missing = [field for field in REQUIRED if not getattr(identity, field, None)]
    if missing:
        reason = "is required before a 履歴書 can be produced"
        raise ValidationFailed([(f"identity.{field}", reason) for field in missing])


def generate(
    session: Session,
    profile: career_models.CareerProfile,
    *,
    date_convention: DateConvention = DateConvention.seireki,
    paper_size: PaperSize = PaperSize.a4,
) -> tuple[bytes, int, Any]:
    """Produce the document. Returns the file, its page count and the snapshot.

    Nothing is retained: the file is streamed to the user and the snapshot is
    what persists (FR-005, FR-016).
    """
    identity = _identity(session, profile)
    _require_identity(identity)

    education = _section(session, profile, career_models.Education)
    experiences = _section(session, profile, career_models.WorkExperience)
    certifications = _section(session, profile, career_models.Certification)

    rows = build_rows(education, experiences)

    # Captured before the render and in the same transaction, so the caller
    # commits both or neither. A render that fails must not leave a record of a
    # document nobody received.
    # The identity leads, because every document carries the name and address
    # whatever else it holds. It is also what keeps a first-time applicant's
    # 履歴書 traceable: with no education and no roles, the identity is the only
    # entry the document used, and a snapshot must name at least one (FR-010).
    used = [identity.id]
    used += [row.source_entry_id for row in rows if row.source_entry_id is not None]
    used += [c.id for c in certifications]

    snapshot = snapshots.capture(
        session,
        profile,
        document_ref=f"rirekisho:{datetime.now(UTC).isoformat()}",
        entry_ids=list(dict.fromkeys(used)),
    )

    pdf, pages = render.render_rirekisho(
        identity={
            "full_name_latin": identity.full_name_latin,
            "full_name_japanese": identity.full_name_japanese,
            "furigana": identity.furigana,
            "date_of_birth": identity.date_of_birth.isoformat() if identity.date_of_birth else None,
            "address": identity.address,
            "phone": identity.phone,
            "email": identity.email,
        },
        rows=rows,
        certifications=[(c.issued_on, c.name) for c in certifications],
        disclosed=None,  # the filter arrives with User Story 3
        era=date_convention is DateConvention.wareki,
        paper=str(paper_size),
    )

    logger.info(
        "rirekisho generated",
        extra={
            "profile_id": profile.id,
            "snapshot_id": snapshot.id,
            "count": pages,
            "outcome": str(date_convention),
        },
    )
    return pdf, pages, snapshot
