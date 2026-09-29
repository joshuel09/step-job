"""Quickstart Scenario 4 — a slow import hands off and still lands.

Most documents finish in the request. The point of the handoff is the one that
does not: it must not become a request that never returns, and the user must be
able to leave without losing it.
"""

import uuid

import pytest
from app.career import service as career_service
from app.core.settings import Settings, get_settings
from app.imports import service
from app.imports.models import ImportStatus, SourceKind

SOURCE = "Software Engineer, Example Corp\nApril 2021 to March 2024\nBuilt internal services."


@pytest.fixture
def profile(session, user_id):
    return career_service.get_or_create_profile(session, user_id)


@pytest.fixture
def forced_handoff(monkeypatch):
    """A zero deadline, so every import takes the background path."""
    settings = Settings(import_deadline_seconds=0)
    monkeypatch.setattr("app.imports.service.get_settings", lambda: settings)
    return settings


@pytest.fixture
def captured_queue(monkeypatch):
    """Capture what would be enqueued, rather than needing a running broker."""
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        "app.imports.queue.enqueue_extraction",
        lambda profile_id, import_id, source: sent.append((profile_id, import_id, source)),
    )
    return sent


def test_a_slow_import_is_handed_off_rather_than_held(
    session, profile, forced_handoff, captured_queue
):
    record = service.create(session, profile, SourceKind.pasted_text)
    result = service.start(session, profile, record, SOURCE)

    # The request returns immediately with something the client can follow.
    assert result.status is ImportStatus.running
    assert not result.is_terminal
    assert len(captured_queue) == 1


def test_the_handoff_carries_the_source_rather_than_storing_it(
    session, profile, forced_handoff, captured_queue
):
    """Storing it would leave a copy of a resume in a table."""
    record = service.create(session, profile, SourceKind.pasted_text)
    service.start(session, profile, record, SOURCE)

    _, import_id, source = captured_queue[0]
    assert import_id == str(record.id)
    assert source == SOURCE

    # And nothing on the record holds it.
    assert SOURCE not in str(record.outcome or "")


def test_a_handed_off_import_can_be_followed(session, profile, forced_handoff, captured_queue):
    record = service.create(session, profile, SourceKind.pasted_text)
    service.start(session, profile, record, SOURCE)

    followed = service.get(session, profile, record.id)
    assert followed.status is ImportStatus.running


def test_an_ordinary_import_still_completes_in_the_request(session, profile):
    """The common case must not pay for the rare one."""
    record = service.create(session, profile, SourceKind.pasted_text)
    result = service.start(session, profile, record, SOURCE)

    assert result.status is ImportStatus.completed
    assert get_settings().import_deadline_seconds > 0


def test_the_actor_name_matches_what_the_worker_defines():
    """The API enqueues by name to keep the dependency one-way.

    That makes the name a contract between two packages, so a rename must break
    this test rather than production.
    """
    import sys
    from pathlib import Path

    from app.imports.queue import EXTRACTION_ACTOR, QUEUE

    worker_path = Path(__file__).resolve().parents[4] / "apps" / "worker"
    sys.path.insert(0, str(worker_path))
    try:
        from worker.extraction import extract_import
    finally:
        sys.path.remove(str(worker_path))

    assert extract_import.actor_name == EXTRACTION_ACTOR
    assert extract_import.queue_name == QUEUE


def test_a_cancelled_import_is_terminal_so_the_worker_skips_it(session, profile):
    record = service.create(session, profile, SourceKind.pasted_text)
    record.status = ImportStatus.running
    session.flush()

    cancelled = service.cancel(session, profile, record.id)

    assert cancelled.is_terminal
    # The actor checks this before running, so a cancelled import that was
    # already queued cannot still produce proposals.


def test_cancelling_a_finished_import_is_a_conflict(session, profile):
    from app.core.errors import ConflictError

    record = service.create(session, profile, SourceKind.pasted_text)
    service.start(session, profile, record, SOURCE)

    with pytest.raises(ConflictError):
        service.cancel(session, profile, record.id)


def test_another_profiles_import_cannot_be_cancelled(session, profile):
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        service.cancel(session, profile, uuid.uuid4())
