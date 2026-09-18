"""Profile and section operations.

Business logic lives here rather than in the router or the web application, per
the constitution: the API is the single source of business rules.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.career import models
from app.career.validation import check_date_range, check_salary_range, normalise_employer
from app.core.errors import NotFoundError, ValidationFailed

SECTION_MODELS: dict[str, type] = {
    "experiences": models.WorkExperience,
    "education": models.Education,
    "certifications": models.Certification,
    "skills": models.Skill,
    "languages": models.Language,
}


def get_or_create_profile(session: Session, user_id: uuid.UUID) -> models.CareerProfile:
    profile = session.scalars(
        select(models.CareerProfile).where(models.CareerProfile.user_id == user_id)
    ).first()
    if profile is None:
        profile = models.CareerProfile(user_id=user_id)
        session.add(profile)
        session.flush()
    return profile


def require_profile(session: Session, user_id: uuid.UUID) -> models.CareerProfile:
    profile = session.scalars(
        select(models.CareerProfile).where(models.CareerProfile.user_id == user_id)
    ).first()
    if profile is None:
        raise NotFoundError("No profile found for this user.")
    return profile


def _owned(session: Session, profile: models.CareerProfile, model: type, entry_id: uuid.UUID):
    """Fetch an entry, scoped to the caller's profile.

    Scoping every lookup by profile is what makes a wrong or guessed identifier a
    404 rather than someone else's career data.
    """
    entry = session.scalars(
        select(model).where(model.id == entry_id, model.profile_id == profile.id)
    ).first()
    if entry is None:
        raise NotFoundError("No such entry in this profile.")
    return entry


# --- work experience -------------------------------------------------------


def _validate_experience(data: dict[str, Any]) -> None:
    failures = check_date_range(data.get("started_on"), data.get("ended_on"))
    if failures:
        raise ValidationFailed(failures)


def create_experience(
    session: Session, profile: models.CareerProfile, data: dict[str, Any]
) -> models.WorkExperience:
    _validate_experience(data)
    entry = models.WorkExperience(
        profile_id=profile.id,
        employer_name_normalised=normalise_employer(data["employer_name"]),
        **data,
    )
    session.add(entry)
    session.flush()
    return entry


def update_experience(
    session: Session, profile: models.CareerProfile, entry_id: uuid.UUID, data: dict[str, Any]
) -> models.WorkExperience:
    entry = _owned(session, profile, models.WorkExperience, entry_id)
    merged = {
        "started_on": data.get("started_on", entry.started_on),
        "ended_on": data.get("ended_on", entry.ended_on),
    }
    _validate_experience(merged)

    for field, value in data.items():
        setattr(entry, field, value)
    if "employer_name" in data:
        entry.employer_name_normalised = normalise_employer(data["employer_name"])
    session.flush()
    return entry


# --- deletion with a reference warning --------------------------------------


@dataclass(frozen=True)
class Reference:
    kind: str
    count: int


def references_to_experience(
    session: Session, profile: models.CareerProfile, entry_id: uuid.UUID
) -> list[Reference]:
    """What depends on this entry.

    FR-013: the user is told what else references an entry before it is removed,
    so deleting a role does not silently take accomplishments with it.
    """
    stories = session.scalar(
        select(func.count())
        .select_from(models.CareerStory)
        .where(
            models.CareerStory.work_experience_id == entry_id,
            models.CareerStory.profile_id == profile.id,
        )
    )
    references = []
    if stories:
        references.append(Reference(kind="career_story", count=stories))
    return references


def delete_experience(
    session: Session, profile: models.CareerProfile, entry_id: uuid.UUID
) -> None:
    entry = _owned(session, profile, models.WorkExperience, entry_id)
    session.delete(entry)
    session.flush()


# --- generic sections -------------------------------------------------------


def create_entry(
    session: Session, profile: models.CareerProfile, section: str, data: dict[str, Any]
):
    model = SECTION_MODELS[section]
    if model is models.Education:
        failures = check_date_range(data.get("started_on"), data.get("ended_on"))
        if failures:
            raise ValidationFailed(failures)
    if model is models.Certification:
        failures = check_date_range(
            data.get("issued_on"),
            data.get("expires_on"),
            start_field="issued_on",
            end_field="expires_on",
        )
        if failures:
            raise ValidationFailed(failures)

    entry = model(profile_id=profile.id, **data)
    session.add(entry)
    session.flush()
    return entry


def update_entry(
    session: Session,
    profile: models.CareerProfile,
    section: str,
    entry_id: uuid.UUID,
    data: dict[str, Any],
):
    entry = _owned(session, profile, SECTION_MODELS[section], entry_id)
    for field, value in data.items():
        setattr(entry, field, value)
    session.flush()
    return entry


def delete_entry(
    session: Session, profile: models.CareerProfile, section: str, entry_id: uuid.UUID
) -> None:
    entry = _owned(session, profile, SECTION_MODELS[section], entry_id)
    session.delete(entry)
    session.flush()


def list_entries(session: Session, profile: models.CareerProfile, section: str) -> list[Any]:
    model = SECTION_MODELS[section]
    return list(session.scalars(select(model).where(model.profile_id == profile.id)))


# --- singleton sections -----------------------------------------------------


def put_singleton(
    session: Session, profile: models.CareerProfile, model: type, data: dict[str, Any]
):
    if model is models.CareerPreference:
        failures = check_salary_range(data.get("salary_min"), data.get("salary_max"))
        if failures:
            raise ValidationFailed(failures)

    existing = session.scalars(
        select(model).where(model.profile_id == profile.id)
    ).first()
    if existing is None:
        existing = model(profile_id=profile.id, **data)
        session.add(existing)
    else:
        for field, value in data.items():
            setattr(existing, field, value)
    session.flush()
    return existing


def get_singleton(session: Session, profile: models.CareerProfile, model: type):
    return session.scalars(select(model).where(model.profile_id == profile.id)).first()


# --- completeness -----------------------------------------------------------


def completeness(session: Session, profile: models.CareerProfile) -> dict[str, dict[str, Any]]:
    """Which sections are empty.

    FR-015: an incomplete profile is valid, and the user can see what is missing
    rather than being blocked from saving.
    """
    report: dict[str, dict[str, Any]] = {}
    for name, model in SECTION_MODELS.items():
        count = session.scalar(
            select(func.count()).select_from(model).where(model.profile_id == profile.id)
        )
        report[name] = {"complete": bool(count), "entry_count": int(count or 0)}

    for name, model in (
        ("identity", models.Identity),
        ("japan", models.JapanProfile),
        ("preferences", models.CareerPreference),
    ):
        present = get_singleton(session, profile, model) is not None
        report[name] = {"complete": present, "entry_count": 1 if present else 0}

    return report
