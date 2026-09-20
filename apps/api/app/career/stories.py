"""Career stories — reusable STAR accomplishments (FR-007).

Users forget what they achieved. A story records the challenge, what the user
did and what resulted, linked to the role it happened in, so that months later
the accomplishment is still there in their own words rather than reconstructed
from memory.

Search matters more here than in other sections: SC-006 expects a user to find
an accomplishment recorded three months earlier in under a minute, and nobody
remembers the title they gave it.
"""

import logging
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.career import models
from app.core.errors import NotFoundError, ValidationFailed

logger = logging.getLogger(__name__)

SEARCHABLE = (
    models.CareerStory.title,
    models.CareerStory.challenge,
    models.CareerStory.action,
    models.CareerStory.result,
)


def _owned_experience(
    session: Session, profile: models.CareerProfile, experience_id: uuid.UUID
) -> models.WorkExperience:
    experience = session.scalars(
        select(models.WorkExperience).where(
            models.WorkExperience.id == experience_id,
            models.WorkExperience.profile_id == profile.id,
        )
    ).first()
    if experience is None:
        # Linking to an experience outside the profile would put a story under a
        # role its author never held.
        raise ValidationFailed([("work_experience_id", "no such experience in this profile")])
    return experience


def get(
    session: Session, profile: models.CareerProfile, story_id: uuid.UUID
) -> models.CareerStory:
    story = session.scalars(
        select(models.CareerStory).where(
            models.CareerStory.id == story_id,
            models.CareerStory.profile_id == profile.id,
        )
    ).first()
    if story is None:
        raise NotFoundError("No such story in this profile.")
    return story


def search(
    session: Session, profile: models.CareerProfile, query: str | None = None
) -> list[models.CareerStory]:
    """Stories, newest first, optionally filtered by keyword.

    Matching runs across all four fields rather than the title alone, because the
    detail a user remembers is usually in the result or the action, not in
    whatever they called it at the time.
    """
    statement = select(models.CareerStory).where(models.CareerStory.profile_id == profile.id)

    if query and query.strip():
        term = f"%{query.strip().lower()}%"
        statement = statement.where(or_(*[func.lower(field).like(term) for field in SEARCHABLE]))

    return list(session.scalars(statement.order_by(models.CareerStory.created_at.desc())))


def create(
    session: Session, profile: models.CareerProfile, data: dict
) -> models.CareerStory:
    experience_id = data.get("work_experience_id")
    if experience_id is not None:
        _owned_experience(session, profile, experience_id)

    story = models.CareerStory(profile_id=profile.id, **data)
    session.add(story)
    session.flush()
    logger.info("story created", extra={"profile_id": profile.id, "entry_id": story.id})
    return story


def update(
    session: Session, profile: models.CareerProfile, story_id: uuid.UUID, data: dict
) -> models.CareerStory:
    story = get(session, profile, story_id)

    if "work_experience_id" in data and data["work_experience_id"] is not None:
        _owned_experience(session, profile, data["work_experience_id"])

    for field, value in data.items():
        setattr(story, field, value)
    session.flush()
    return story


def delete(session: Session, profile: models.CareerProfile, story_id: uuid.UUID) -> None:
    story = get(session, profile, story_id)
    session.delete(story)
    session.flush()
    logger.info("story deleted", extra={"profile_id": profile.id, "entry_id": story_id})


def reassign_to_surviving_experience(
    session: Session, profile: models.CareerProfile, merged_id: uuid.UUID, surviving_id: uuid.UUID
) -> int:
    """Move stories when two experiences are merged.

    A story written against a role that later turns out to be a duplicate must
    follow the surviving entry rather than be orphaned (spec edge cases). Used by
    the proposal merge in User Story 3.
    """
    stories = list(
        session.scalars(
            select(models.CareerStory).where(
                models.CareerStory.work_experience_id == merged_id,
                models.CareerStory.profile_id == profile.id,
            )
        )
    )
    for story in stories:
        story.work_experience_id = surviving_id
    session.flush()
    return len(stories)
