"""The 30-day purge.

FR-025 promises that everything remaining after the recovery window is erased
without further action by the user. The settings page states that promise to
users in as many words, so these tests are what keep it true.
"""

from datetime import UTC, datetime, timedelta

from app.career.models import CareerProfile, EntrySnapshot, Identity
from app.db.soft_delete import with_deleted
from sqlalchemy import select
from worker.purge import find_due, purge_due_profiles


def _deleted_profile(session, *, days_ago: int) -> CareerProfile:
    """A profile deleted far enough in the past that its window has closed."""
    deleted_at = datetime.now(UTC) - timedelta(days=days_ago)
    profile = CareerProfile(
        user_id=__import__("uuid").uuid4(),
        deleted_at=deleted_at,
        purge_after=deleted_at + timedelta(days=30),
    )
    session.add(profile)
    session.flush()
    return profile


def _active_profile(session) -> CareerProfile:
    profile = CareerProfile(user_id=__import__("uuid").uuid4())
    session.add(profile)
    session.flush()
    return profile


def test_a_profile_past_its_window_is_found(session):
    profile = _deleted_profile(session, days_ago=31)
    assert [p.id for p in find_due(session)] == [profile.id]


def test_a_profile_inside_its_window_is_left_alone(session):
    _deleted_profile(session, days_ago=10)
    assert find_due(session) == []


def test_an_active_profile_is_never_due(session):
    _active_profile(session)
    assert find_due(session) == []


def test_the_boundary_is_not_crossed_early(session):
    """A profile deleted exactly 30 days ago is due; 29 days is not."""
    _deleted_profile(session, days_ago=29)
    assert find_due(session) == []

    _deleted_profile(session, days_ago=30)
    assert len(find_due(session)) == 1


def test_purging_erases_the_profile(session):
    profile = _deleted_profile(session, days_ago=31)
    profile_id = profile.id

    assert purge_due_profiles(session) == 1

    with with_deleted(session):
        remaining = session.scalars(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        ).first()
    assert remaining is None


def test_purging_cascades_to_everything_beneath_the_profile(session):
    """FR-031: nothing may be left orphaned still holding career data."""
    profile = _deleted_profile(session, days_ago=31)
    session.add(Identity(profile_id=profile.id, full_name_latin="Example Person"))
    session.add(
        EntrySnapshot(
            profile_id=profile.id,
            document_ref="test",
            captured_at=datetime.now(UTC),
            captured_entry_ids=[],
            payload={},
        )
    )
    session.flush()

    purge_due_profiles(session)

    assert session.scalars(select(Identity)).all() == []
    assert session.scalars(select(EntrySnapshot)).all() == []


def test_purging_is_idempotent(session):
    """A retry after a partial failure, or a scheduler firing twice, must be safe."""
    _deleted_profile(session, days_ago=31)

    assert purge_due_profiles(session) == 1
    assert purge_due_profiles(session) == 0
    assert purge_due_profiles(session) == 0


def test_purging_an_empty_queue_is_not_an_error(session):
    assert purge_due_profiles(session) == 0


def test_purging_does_not_touch_profiles_that_are_not_due(session):
    due = _deleted_profile(session, days_ago=31)
    safe = _deleted_profile(session, days_ago=5)
    active = _active_profile(session)

    assert purge_due_profiles(session) == 1

    with with_deleted(session):
        survivors = {p.id for p in session.scalars(select(CareerProfile))}
    assert due.id not in survivors
    assert {safe.id, active.id} <= survivors
