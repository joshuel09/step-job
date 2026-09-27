"""Quickstart Scenario 6 — failures say which kind of failure they are.

"We could not read your document" and "our service is down" produce the same
blank screen, and only one of them is worth coming back for. Keeping them apart
is the whole reason FailureReason has more than one value (FR-017b).
"""

import pytest
from app.ai.fake import FakeAIProvider, FakeBehaviour
from app.career import proposals
from app.career import service as career_service
from app.core.settings import get_settings
from app.imports import service
from app.imports.models import FailureReason, ImportStatus, SourceKind

SOURCE = "Software Engineer, Example Corp\nApril 2021 to March 2024\nBuilt internal services."


@pytest.fixture
def profile(session, user_id):
    return career_service.get_or_create_profile(session, user_id)


def _run(session, profile, provider):
    record = service.create(session, profile, SourceKind.pasted_text)
    return service.run(session, profile, record, SOURCE, provider)


def test_a_persistent_outage_is_reported_as_the_service_being_down(session, profile):
    record = _run(session, profile, FakeAIProvider(FakeBehaviour.unavailable))

    assert record.status is ImportStatus.failed
    assert record.failure_reason is FailureReason.service_unavailable
    # Distinguishable from a document problem, which is the point.
    assert record.failure_reason is not FailureReason.unreadable_document
    assert "later" in record.outcome["message"]


def test_an_outage_is_retried_a_bounded_number_of_times(session, profile):
    provider = FakeAIProvider(FakeBehaviour.unavailable)
    _run(session, profile, provider)

    attempts = max(1, get_settings().ai_max_retries)
    assert provider.calls == attempts, "retries must be bounded, and must happen"


def test_a_transient_outage_costs_the_user_nothing(session, profile):
    """A brief blip should not lose someone a long import."""
    provider = FakeAIProvider(FakeBehaviour.extract, fail_times=1)

    record = _run(session, profile, provider)

    assert record.status is ImportStatus.completed
    assert provider.calls == 2, "the first attempt failed and the second succeeded"
    assert len(proposals.list_for(session, profile)) == 1


def test_an_unusable_response_is_not_reported_as_an_outage(session, profile):
    """The service answered; it just answered with nonsense."""
    record = _run(session, profile, FakeAIProvider(FakeBehaviour.invalid))

    assert record.failure_reason is FailureReason.extraction_failed
    assert record.failure_reason is not FailureReason.service_unavailable


def test_a_readable_document_with_nothing_in_it_says_so(session, profile):
    record = _run(session, profile, FakeAIProvider(FakeBehaviour.empty))

    assert record.failure_reason is FailureReason.no_career_information
    assert record.entry_count == 0


@pytest.mark.parametrize(
    "behaviour",
    [FakeBehaviour.unavailable, FakeBehaviour.invalid, FakeBehaviour.empty],
)
def test_no_failure_leaves_a_partial_set_of_proposals(session, profile, behaviour):
    """FR-017: a partial set is indistinguishable from a complete one."""
    _run(session, profile, FakeAIProvider(behaviour))

    assert proposals.list_for(session, profile) == []


@pytest.mark.parametrize(
    "behaviour",
    [FakeBehaviour.unavailable, FakeBehaviour.invalid, FakeBehaviour.empty],
)
def test_every_failure_reaches_a_terminal_state(session, profile, behaviour):
    """SC-007: nothing is left running."""
    record = _run(session, profile, FakeAIProvider(behaviour))

    assert record.is_terminal
    assert record.completed_at is not None


def test_a_failed_import_still_appears_in_the_history(session, profile):
    """A user who tried and failed should be able to see that they tried."""
    _run(session, profile, FakeAIProvider(FakeBehaviour.unavailable))

    history = service.list_for(session, profile)
    assert len(history) == 1
    assert history[0].status is ImportStatus.failed
