"""Producing a 職務経歴書.

Gathers what the profile holds, projects the sections, captures a snapshot of
the entries used, and renders. The snapshot and the render happen in one
transaction, so a render that fails leaves no record of a document that never
existed (research.md R-006, as feature 003 established).

The second consumer of the Master Career Profile, and it adds no table and no
column. That is Principle I working: another document is another reader, never
another place to describe a career.
"""

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career import models as career_models
from app.career import snapshots
from app.core.errors import ValidationFailed
from app.shokumu import render, sections, summary
from app.shokumu.schemas import Arrangement, DateConvention, PaperSize

logger = logging.getLogger(__name__)


def _section(session: Session, profile: career_models.CareerProfile, model: type) -> list[Any]:
    return list(session.scalars(select(model).where(model.profile_id == profile.id)))


def _identity(session: Session, profile: career_models.CareerProfile):
    return session.scalars(
        select(career_models.Identity).where(career_models.Identity.profile_id == profile.id)
    ).first()


def _require(identity, experiences: list[Any], profile_id) -> None:
    """Refuse rather than produce a document that is not the document (FR-006).

    Two things a 職務経歴書 cannot be meaningful without: a name to put at the
    top, and some career history to describe. Both are named rather than
    reported generically, so the user knows what to go and record.
    """
    failures: list[tuple[str, str]] = []

    if identity is None or not (identity.full_name_latin or "").strip():
        failures.append(("identity", "add your name before generating a 職務経歴書"))

    # A 職務経歴書 with no work history is not a sparse document; it is a
    # different document. Producing an empty one would be a blank page with
    # headings on it.
    if not experiences:
        failures.append(("experiences", "a 職務経歴書 needs at least one employer"))

    if not failures:
        return

    # How many things stood in the way, never which: a field name says what
    # part of someone's history they have not recorded yet.
    logger.info(
        "shokumu-keirekisho refused",
        extra={"profile_id": profile_id, "outcome": "missing_required", "count": len(failures)},
    )
    raise ValidationFailed(
        failures, "A 職務経歴書 cannot be produced from what this profile holds."
    )


def build(
    session: Session,
    profile: career_models.CareerProfile,
    *,
    arrangement: Arrangement = Arrangement.reverse_chronological,
) -> tuple[Any, sections.CareerHistory, summary.Summary]:
    """The identity, the projected history and the summary, with nothing drawn.

    Separate from `generate` so the projection can be read without producing a
    document — the readiness report and the tests both want it.
    """
    identity = _identity(session, profile)
    experiences = _section(session, profile, career_models.WorkExperience)
    _require(identity, experiences, profile.id)

    history = sections.build_history(
        experiences,
        _section(session, profile, career_models.CareerStory),
        skills=_section(session, profile, career_models.Skill),
        languages=_section(session, profile, career_models.Language),
        certifications=_section(session, profile, career_models.Certification),
        newest_first=arrangement is Arrangement.reverse_chronological,
    )
    return identity, history, summary.build_summary(experiences)


def generate(
    session: Session,
    profile: career_models.CareerProfile,
    *,
    arrangement: Arrangement = Arrangement.reverse_chronological,
    date_convention: DateConvention = DateConvention.seireki,
    paper_size: PaperSize = PaperSize.a4,
    today: date | None = None,
) -> tuple[bytes, int, Any]:
    """Produce the document. Returns the file, its page count and the snapshot.

    Nothing is retained: the file is streamed to the user and the snapshot is
    what persists (FR-005, FR-017).
    """
    identity, history, facts = build(session, profile, arrangement=arrangement)

    # Captured before the render and in the same transaction, so the caller
    # commits both or neither. The identity leads, because every document
    # carries the name whatever else it holds — and because `capture` refuses
    # an empty list, which a profile with nothing but one employer could
    # otherwise reach (R-006).
    used = [identity.id, *history.entry_ids()]

    snapshot = snapshots.capture(
        session,
        profile,
        document_ref=f"shokumu-keirekisho:{datetime.now(UTC).isoformat()}",
        entry_ids=list(dict.fromkeys(used)),
    )

    pdf, pages = render.render_shokumu_keirekisho(
        name=identity.full_name_japanese or identity.full_name_latin,
        history=history,
        summary=facts,
        era=date_convention is DateConvention.wareki,
        paper=str(paper_size),
        today=today,
    )

    logger.info(
        "shokumu-keirekisho generated",
        extra={
            "profile_id": profile.id,
            "snapshot_id": snapshot.id,
            "count": pages,
            "outcome": str(arrangement),
        },
    )
    return pdf, pages, snapshot
