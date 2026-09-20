"""Deciding whether a proposed role is one the profile already holds.

Clarification Q4 settled the rule: the same employer with overlapping dates,
regardless of how the job title is worded. Matching on title as well fails
exactly where it matters, because two sources routinely describe one role
differently — "Software Engineer" and "Backend Engineer" are often the same job.

The rule cuts the other way too. Two spells at one employer that do not overlap
are a promotion or a return, and merging them would destroy real career history
(FR-033).
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career import models
from app.career.validation import normalise_employer

# A role with no end date is still being held, so it extends to the present for
# overlap purposes. Without this, a current role could never match anything.
_OPEN_ENDED = date.max


def ranges_overlap(
    a_start: date, a_end: date | None, b_start: date, b_end: date | None
) -> bool:
    return a_start <= (b_end or _OPEN_ENDED) and b_start <= (a_end or _OPEN_ENDED)


def find_duplicate_experience(
    session: Session,
    profile: models.CareerProfile,
    employer_name: str,
    started_on: date,
    ended_on: date | None,
) -> uuid.UUID | None:
    """The existing experience a proposal probably duplicates, if any."""
    normalised = normalise_employer(employer_name)
    if not normalised:
        return None

    candidates = session.scalars(
        select(models.WorkExperience).where(
            models.WorkExperience.profile_id == profile.id,
            models.WorkExperience.employer_name_normalised == normalised,
        )
    )

    for candidate in candidates:
        if ranges_overlap(started_on, ended_on, candidate.started_on, candidate.ended_on):
            return candidate.id
    return None


def _as_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def detect(
    session: Session, profile: models.CareerProfile, entry_type: str, payload: dict
) -> uuid.UUID | None:
    """Flag a possible duplicate for a proposal, or None.

    Only work experience is compared. The other sections have no equivalent of
    "the same role described twice", and guessing at one would produce merge
    suggestions a user cannot evaluate.
    """
    if entry_type != models.ProposedEntryType.work_experience:
        return None

    employer = payload.get("employer_name")
    started = _as_date(payload.get("started_on"))
    if not employer or started is None:
        return None

    return find_duplicate_experience(
        session, profile, employer, started, _as_date(payload.get("ended_on"))
    )
