"""The review queue.

Entries proposed by an outside source wait here. Nothing enters the profile
until the user accepts it (FR-018), and what enters is the version the user
approved — corrections included — never the original suggestion (FR-019).

This is the contract an import feature delivers into. Extracting career
information from resumes or pasted text is a separate feature; this module only
defines what happens to a suggestion once it exists.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career import duplicates, models, service, stories
from app.core.errors import ConflictError, NotFoundError, ValidationFailed

logger = logging.getLogger(__name__)

# Which model an accepted proposal becomes, and which section it belongs to.
TARGETS: dict[models.ProposedEntryType, tuple[type, str | None]] = {
    models.ProposedEntryType.work_experience: (models.WorkExperience, "experiences"),
    models.ProposedEntryType.education: (models.Education, "education"),
    models.ProposedEntryType.certification: (models.Certification, "certifications"),
    models.ProposedEntryType.skill: (models.Skill, "skills"),
    models.ProposedEntryType.language: (models.Language, "languages"),
    models.ProposedEntryType.career_story: (models.CareerStory, None),
}


def list_for(
    session: Session,
    profile: models.CareerProfile,
    status: models.ProposalStatus = models.ProposalStatus.pending,
) -> list[models.ProposedEntry]:
    return list(
        session.scalars(
            select(models.ProposedEntry)
            .where(
                models.ProposedEntry.profile_id == profile.id,
                models.ProposedEntry.status == status,
            )
            .order_by(models.ProposedEntry.created_at.desc())
        )
    )


def get(
    session: Session, profile: models.CareerProfile, proposal_id: uuid.UUID
) -> models.ProposedEntry:
    proposal = session.scalars(
        select(models.ProposedEntry).where(
            models.ProposedEntry.id == proposal_id,
            models.ProposedEntry.profile_id == profile.id,
        )
    ).first()
    if proposal is None:
        raise NotFoundError("No such proposal in this profile.")
    return proposal


def _record_decision(proposal: models.ProposedEntry, status: models.ProposalStatus) -> None:
    """Mark a proposal reviewed and discard its evidence.

    Feature 002 attaches, to each proposal, the passages of source text its
    values came from. That evidence exists so the user can judge a value before
    accepting it. Once the decision is made it is only a fragment of someone's
    resume — which may state residence status, an address or a previous salary —
    with no remaining purpose (FR-015a of feature 002).

    Cleared here, in the same call that records the decision, so the two cannot
    come apart: the caller commits one transaction, and a process dying
    immediately afterwards cannot leave evidence behind a reviewed proposal.

    The accepted entry is untouched. What the user approved stays as approved.
    """
    proposal.status = status
    proposal.reviewed_at = datetime.now(UTC)
    proposal.evidence = None


def _require_pending(proposal: models.ProposedEntry) -> None:
    if proposal.is_reviewed:
        # Accepted and rejected are terminal: a decision is not revisited, and a
        # double submit must not create a second entry.
        raise ConflictError("This proposal has already been reviewed.")


def submit(
    session: Session, profile: models.CareerProfile, items: list[dict[str, Any]]
) -> list[models.ProposedEntry]:
    """Queue proposals, flagging any that look like something already held."""
    created: list[models.ProposedEntry] = []

    for item in items:
        entry_type = models.ProposedEntryType(item["entry_type"])
        payload = item["payload"]

        proposal = models.ProposedEntry(
            profile_id=profile.id,
            entry_type=entry_type,
            source=item["source"],
            payload=payload,
            possible_duplicate_of=duplicates.detect(session, profile, entry_type, payload),
        )
        session.add(proposal)
        created.append(proposal)

    session.flush()
    logger.info(
        "proposals queued",
        extra={"profile_id": profile.id, "count": len(created)},
    )
    return created


def _build_entry(
    session: Session, profile: models.CareerProfile, proposal: models.ProposedEntry, payload: dict
) -> Any:
    model, _section = TARGETS[proposal.entry_type]

    if model is models.WorkExperience:
        return service.create_experience(session, profile, payload)
    if model is models.CareerStory:
        return stories.create(session, profile, payload)

    return service.create_entry(session, profile, TARGETS[proposal.entry_type][1], payload)


def accept(
    session: Session,
    profile: models.CareerProfile,
    proposal_id: uuid.UUID,
    corrections: dict | None = None,
) -> tuple[models.ProposedEntry, Any]:
    """Accept a proposal, writing the user's version of it.

    Corrections replace the proposed values. The original suggestion is not kept
    as profile data — what the user approved is what the profile holds (FR-019).
    """
    proposal = get(session, profile, proposal_id)
    _require_pending(proposal)

    payload = {**proposal.payload, **(corrections or {})}

    try:
        entry = _build_entry(session, profile, proposal, payload)
    except TypeError as error:
        raise ValidationFailed([("payload", f"cannot be accepted as written: {error}")]) from error

    _record_decision(proposal, models.ProposalStatus.accepted)
    session.flush()

    logger.info(
        "proposal accepted",
        extra={
            "profile_id": profile.id,
            "entry_id": entry.id,
            "entry_type": proposal.entry_type,
            "outcome": "accepted",
        },
    )
    return proposal, entry


def reject(session: Session, profile: models.CareerProfile, proposal_id: uuid.UUID) -> None:
    proposal = get(session, profile, proposal_id)
    _require_pending(proposal)

    _record_decision(proposal, models.ProposalStatus.rejected)
    session.flush()

    logger.info(
        "proposal rejected",
        extra={"profile_id": profile.id, "outcome": "rejected"},
    )


def merge(
    session: Session,
    profile: models.CareerProfile,
    proposal_id: uuid.UUID,
    target_entry_id: uuid.UUID,
    payload: dict | None = None,
) -> models.WorkExperience:
    """Fold a proposal into an existing entry, at the user's choosing.

    Never automatic (FR-034). Keeping both remains available by accepting
    instead, which is why this is a separate call rather than a flag.
    """
    proposal = get(session, profile, proposal_id)
    _require_pending(proposal)

    if proposal.entry_type is not models.ProposedEntryType.work_experience:
        raise ValidationFailed([("proposal", "only work experience can be merged")])

    merged = {**proposal.payload, **(payload or {})}
    merged.pop("source_language", None)

    entry = service.update_experience(session, profile, target_entry_id, merged)

    _record_decision(proposal, models.ProposalStatus.accepted)
    session.flush()

    logger.info(
        "proposal merged",
        extra={"profile_id": profile.id, "entry_id": entry.id, "outcome": "merged"},
    )
    return entry


def merge_experiences(
    session: Session,
    profile: models.CareerProfile,
    losing_id: uuid.UUID,
    surviving_id: uuid.UUID,
) -> int:
    """Combine two existing roles, keeping accomplishments attached.

    A story written against a role that turns out to be a duplicate follows the
    surviving entry rather than being orphaned (spec edge cases).
    """
    moved = stories.reassign_to_surviving_experience(session, profile, losing_id, surviving_id)
    service.delete_experience(session, profile, losing_id)
    return moved
