"""Deleting and restoring a profile.

Deletion splits in two because the two classes of data carry different
obligations (FR-024, FR-025, research.md R-002).

Residence status, nationality, visa type and visa expiry are destroyed on the
request path, inside the same transaction that marks the profile deleted. They do
not wait on a scheduler: if the purge job never runs, that data is still gone.

Everything else is soft deleted and swept by the purge job once the recovery
window closes. Reads exclude soft-deleted profiles at the data-access layer
(see db/soft_delete.py), so FR-027 holds without each endpoint remembering.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career.models import CareerProfile, JapanProfile
from app.core.errors import ConflictError, NotFoundError
from app.core.settings import get_settings
from app.db.soft_delete import with_deleted

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeletionReceipt:
    """What the user is owed before and after deletion (FR-026)."""

    erased_immediately: list[str]
    recoverable_until: datetime


def delete_profile(session: Session, profile: CareerProfile) -> DeletionReceipt:
    if profile.deleted_at is not None:
        raise ConflictError("This profile is already deleted.")

    now = datetime.now(UTC)
    window = timedelta(days=get_settings().deletion_recovery_days)

    erased = _erase_sensitive_fields(session, profile)

    profile.deleted_at = now
    profile.purge_after = now + window
    session.flush()

    logger.info(
        "profile deleted",
        extra={"profile_id": profile.id, "count": len(erased), "outcome": "soft_deleted"},
    )

    return DeletionReceipt(erased_immediately=erased, recoverable_until=profile.purge_after)


def _erase_sensitive_fields(session: Session, profile: CareerProfile) -> list[str]:
    """Destroy the immigration-related fields now, not on a schedule."""
    japan = session.scalars(
        select(JapanProfile).where(JapanProfile.profile_id == profile.id)
    ).first()
    if japan is None:
        return list(JapanProfile.IMMEDIATELY_ERASED)

    for field in JapanProfile.IMMEDIATELY_ERASED:
        setattr(japan, field, None)
    session.flush()
    return list(JapanProfile.IMMEDIATELY_ERASED)


def restore_profile(session: Session, user_id) -> CareerProfile:
    """Bring a profile back inside its recovery window.

    Recovers everything still held. It cannot recover the immediately-erased
    fields, because they no longer exist — the user was told so at deletion.
    """
    with with_deleted(session):
        profile = session.scalars(
            select(CareerProfile).where(CareerProfile.user_id == user_id)
        ).first()

        if profile is None:
            raise NotFoundError("No profile found for this user.")
        if profile.deleted_at is None:
            raise ConflictError("This profile is not deleted.")
        if profile.purge_after is not None and profile.purge_after <= datetime.now(UTC):
            raise ConflictError("The recovery window has passed; this profile is gone.")

        profile.deleted_at = None
        profile.purge_after = None
        session.flush()

    return profile
