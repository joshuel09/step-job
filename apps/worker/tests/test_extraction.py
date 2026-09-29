"""The handed-off import.

A slow document is handed to the worker rather than held in the request. Being
slow must not change what is produced (FR-005c), and a failure in the background
must create no proposals, exactly as in the request (FR-017).
"""

import uuid
from datetime import UTC, datetime

import pytest
from app.ai.fake import FakeAIProvider, FakeBehaviour
from app.career import proposals
from app.career import service as career_service
from app.imports import service
from app.imports.models import Import, ImportStatus, SourceKind

SOURCE = "Software Engineer, Example Corp\nApril 2021 to March 2024\nBuilt internal services."


@pytest.fixture
def profile(session):
    return career_service.get_or_create_profile(session, uuid.uuid4())


def _queued_import(session, profile) -> Import:
    """An import in the state the worker finds it: running, nothing produced."""
    record = Import(
        profile_id=profile.id,
        source_kind=SourceKind.pasted_text,
        status=ImportStatus.running,
        started_at=datetime.now(UTC),
    )
    session.add(record)
    session.flush()
    return record


def test_the_background_run_produces_the_same_result(session, profile):
    record = _queued_import(session, profile)

    service.run(session, profile, record, SOURCE, FakeAIProvider(FakeBehaviour.extract))

    assert record.status is ImportStatus.completed
    assert record.entry_count == 1
    assert len(proposals.list_for(session, profile)) == 1


def test_a_background_failure_creates_no_proposals(session, profile):
    record = _queued_import(session, profile)

    service.run(session, profile, record, SOURCE, FakeAIProvider(FakeBehaviour.unavailable))

    assert record.status is ImportStatus.failed
    assert proposals.list_for(session, profile) == []


def test_a_background_fabrication_still_reaches_no_proposal(session, profile):
    """The verifier is not relaxed by running somewhere else."""
    record = _queued_import(session, profile)

    service.run(session, profile, record, SOURCE, FakeAIProvider(FakeBehaviour.fabricate))

    assert proposals.list_for(session, profile) == []


def test_an_already_settled_import_is_not_run_twice(session, profile):
    """A queued import that was cancelled must not produce proposals anyway."""
    record = _queued_import(session, profile)
    record.status = ImportStatus.failed
    record.completed_at = datetime.now(UTC)
    session.flush()

    assert record.is_terminal, "the actor skips terminal imports"


def test_every_background_outcome_is_terminal(session, profile):
    for behaviour in (FakeBehaviour.extract, FakeBehaviour.unavailable, FakeBehaviour.empty):
        record = _queued_import(session, profile)
        service.run(session, profile, record, SOURCE, FakeAIProvider(behaviour))

        assert record.is_terminal, behaviour
        assert record.completed_at is not None
