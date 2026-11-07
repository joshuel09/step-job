"""Producing an English resume.

Gathers what the profile holds, projects it, captures a record of what the
document said, and renders. The snapshot and the render happen in one
transaction, so a render that fails leaves no record of a document that
never existed — the boundary features 003 and 004 established.

The third reader of the Master Career Profile. It adds no table and no
column of its own: feature 005's storage went in during Phase 2 and is read
here like any other part of the profile (Principle I).

**No provider is reachable from this package.** Generation reads approved
English and renders it; a missing version is reported by readiness, never
translated on the spot (FR-017, R-005). That is not a rule this module
follows — `tests/unit/test_ai_boundary.py` walks the imports under
`app/resume/` and fails the build if `app.ai` is reachable from any of them,
transitively and through package initialisers.
"""

import logging
from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career import models as career_models
from app.career import snapshots
from app.career.models import Locale
from app.core.errors import ValidationFailed
from app.resume import readiness, render, sections
from app.resume.schemas import PaperSize, ResumeReadinessReport
from app.translations import service as translations
from app.translations.models import EntryTranslation

logger = logging.getLogger(__name__)

#: What this document's snapshots are labelled with. A fixed string rather
#: than one carrying a timestamp: the row already records `captured_at`, and
#: a value that varies cannot be queried for.
DOCUMENT_REF = "english-resume"

# Why each missing thing stops a document, in the words the user reads.
REASONS = {
    "identity": "add your name before generating a resume",
    # A resume with no work history is not a sparse resume; it is a blank
    # page with headings on it.
    "experiences": "a resume needs at least one role",
}


def _section(session: Session, profile: career_models.CareerProfile, model: type) -> list[Any]:
    return list(session.scalars(select(model).where(model.profile_id == profile.id)))


def _identity(session: Session, profile: career_models.CareerProfile):
    return session.scalars(
        select(career_models.Identity).where(career_models.Identity.profile_id == profile.id)
    ).first()


def _approved_english(
    session: Session, profile: career_models.CareerProfile
) -> list[EntryTranslation]:
    """Every English version this profile holds.

    Filtered by language in the query as well as in `Approved`, so the
    `(profile_id, language)` index is the one used rather than a scan of
    every approval the profile has in any language.
    """
    return list(
        session.scalars(
            select(EntryTranslation).where(
                EntryTranslation.profile_id == profile.id,
                EntryTranslation.language == Locale.en,
            )
        )
    )


def _require(identity, experiences: list[Any], profile_id) -> None:
    """Refuse rather than produce something that is not a resume (FR-006).

    The rule lives in readiness.py, so the report a user reads before
    generating and the refusal they would meet cannot disagree.
    """
    missing = readiness.missing_required(identity, experiences)
    if not missing:
        return

    failures = [(field, REASONS[field]) for field in missing]
    # How many things stood in the way, never which: a field name says what
    # part of someone's history they have not recorded yet.
    logger.info(
        "resume refused",
        extra={"profile_id": profile_id, "outcome": "missing_required", "count": len(failures)},
    )
    raise ValidationFailed(failures, "A resume cannot be produced from what this profile holds.")


def build(
    session: Session,
    profile: career_models.CareerProfile,
    *,
    include_skills: bool = True,
) -> sections.ResumeContent:
    """What the renderer will be given, with nothing drawn.

    Separate from `generate` so the projection can be read without producing
    a document — readiness and the tests both want it.
    """
    identity = _identity(session, profile)
    experiences = _section(session, profile, career_models.WorkExperience)
    _require(identity, experiences, profile.id)

    return sections.build_content(
        identity,
        experiences=experiences,
        education=_section(session, profile, career_models.Education),
        skills=_section(session, profile, career_models.Skill),
        certifications=_section(session, profile, career_models.Certification),
        translations=_approved_english(session, profile),
        include_skills=include_skills,
    )


def readiness_report(
    session: Session, profile: career_models.CareerProfile
) -> ResumeReadinessReport:
    """What the user should know before asking for a document (FR-020).

    Read-only, and it does not raise. `build` refuses a profile with no
    name or no roles, which is right — it is about to produce a document —
    but a readiness report asked by a profile in exactly that state is the
    request that most needs answering, and `can_generate` is how it
    answers.
    """
    return readiness.build_report(
        _identity(session, profile),
        experiences=_section(session, profile, career_models.WorkExperience),
        education=_section(session, profile, career_models.Education),
        skills=_section(session, profile, career_models.Skill),
        certifications=_section(session, profile, career_models.Certification),
        stored=translations.stored_for_profile(session, profile.id),
    )


def generate(
    session: Session,
    profile: career_models.CareerProfile,
    *,
    paper_size: PaperSize = PaperSize.letter,
    include_skills: bool = True,
) -> tuple[bytes, int, Any]:
    """Produce the document. Returns the file, its page count and the snapshot.

    Nothing is retained: the file is streamed to the user and the snapshot
    is what persists (FR-005, FR-015).
    """
    content = build(session, profile, include_skills=include_skills)

    # Captured before the render and in the same transaction, so the caller
    # commits both or neither. The identity leads, because every document
    # carries the name whatever else it holds — and because `capture`
    # refuses an empty list, which a profile holding only an identity could
    # otherwise reach.
    used = [content.contact.source_entry_id, *_rendered_ids(content)]

    # The entries alone are not enough. `capture` serialises what the rows
    # hold, which for a Japanese profile is the Japanese — so a snapshot of
    # entry ids would, after the user edits an approval, describe a document
    # that no longer resembles what was sent. The rendered content goes in
    # beside them: the English that was actually printed, as it was printed
    # (R-010, SC-008).
    snapshot = snapshots.capture(
        session,
        profile,
        document_ref=DOCUMENT_REF,
        entry_ids=list(dict.fromkeys(used)),
        # The identity narrowed to what this document uses. FR-009 is about
        # the page, and a snapshot is not the page — but copying a date of
        # birth and an address into a stored row because the resume happened
        # to need the name beside them is a second place that data lives,
        # outliving the user clearing it from their profile. The document
        # prints three fields; the record of it holds three fields.
        fields={content.contact.source_entry_id: ("full_name_latin", "email", "phone")},
        rendered=_as_payload(content),
    )

    pdf, pages = render.render_resume(content, paper=str(paper_size))

    logger.info(
        "resume generated",
        extra={
            "profile_id": profile.id,
            "snapshot_id": snapshot.id,
            "count": pages,
            "outcome": str(paper_size),
        },
    )
    return pdf, pages, snapshot


def _rendered_ids(content: sections.ResumeContent) -> list[Any]:
    """Every entry the document drew on, in render order."""
    return [
        entry.source_entry_id
        for group in (
            content.experiences,
            content.education,
            content.skills,
            content.certifications,
        )
        for entry in group
    ]


def _as_payload(content: sections.ResumeContent) -> dict[str, Any]:
    """The rendered content as plain JSON, for the snapshot row.

    Dates become ISO strings and ids become their text form; a dataclass of
    `uuid.UUID` and `date` is not something a JSON column will take.
    """
    return _plain(asdict(content))


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "hex"):
        return str(value)
    return value
