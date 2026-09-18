"""FR-027: a soft-deleted profile must be unreadable by every other feature.

This is enforced at the data-access layer rather than per endpoint, so these
tests exercise the filter directly — if it regresses, deleted career data starts
leaking into ordinary reads.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.career.models import CareerProfile
from app.db.soft_delete import with_deleted
from sqlalchemy import select


def _profile(session) -> CareerProfile:
    profile = CareerProfile(user_id=uuid.uuid4())
    session.add(profile)
    session.flush()
    return profile


def test_active_profile_is_visible(session):
    profile = _profile(session)
    found = session.scalars(select(CareerProfile).where(CareerProfile.id == profile.id)).first()
    assert found is not None


def test_soft_deleted_profile_is_invisible_to_ordinary_reads(session):
    profile = _profile(session)
    profile.deleted_at = datetime.now(UTC)
    profile.purge_after = profile.deleted_at + timedelta(days=30)
    session.flush()

    found = session.scalars(select(CareerProfile).where(CareerProfile.id == profile.id)).first()
    assert found is None, "a soft-deleted profile leaked into an ordinary read"


def test_purge_and_restore_can_opt_in_to_seeing_deleted(session):
    profile = _profile(session)
    profile.deleted_at = datetime.now(UTC)
    session.flush()

    with with_deleted(session):
        found = session.scalars(select(CareerProfile).where(CareerProfile.id == profile.id)).first()
    assert found is not None, "restore and purge must still be able to find the profile"

    # The opt-in must not persist beyond the block.
    after = session.scalars(select(CareerProfile).where(CareerProfile.id == profile.id)).first()
    assert after is None
