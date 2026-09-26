"""Quickstart Scenario 2 — a fabricated field never becomes a proposal.

The verifier has its own unit tests. These are different: they run the whole
path — provider, verification, deduplication, proposal creation — and assert
that a fabrication cannot reach the review queue through any of it.

A unit test proves the verifier rejects a bad quote. Only this proves nothing
downstream puts the value back.
"""

import pytest
from app.ai.fake import FakeAIProvider, FakeBehaviour
from app.career import proposals
from app.career import service as career_service
from app.imports import service
from app.imports.models import FailureReason, ImportStatus, SourceKind

SOURCE = "Software Engineer, Example Corp. April 2021 to March 2024."


@pytest.fixture
def profile(session, user_id):
    return career_service.get_or_create_profile(session, user_id)


def _run(session, profile, behaviour: FakeBehaviour):
    record = service.create(session, profile, SourceKind.pasted_text)
    return service.run(session, profile, record, SOURCE, FakeAIProvider(behaviour))


def test_an_honest_extraction_produces_a_proposal_with_evidence(session, profile):
    record = _run(session, profile, FakeBehaviour.extract)
    assert record.status is ImportStatus.completed

    queued = proposals.list_for(session, profile)
    assert len(queued) == 1
    assert queued[0].evidence, "a proposal must carry the passages its values came from"


def test_a_fabricated_field_never_reaches_the_review_queue(session, profile):
    """The whole point of the feature's design."""
    record = _run(session, profile, FakeBehaviour.fabricate)

    # Every field failed verification, so there was nothing to propose.
    assert record.status is ImportStatus.failed
    assert record.failure_reason is FailureReason.no_career_information
    assert proposals.list_for(session, profile) == []


def test_a_near_miss_quote_never_reaches_the_review_queue(session, profile):
    """A plausible-but-absent quote is what a similarity score would admit."""
    record = _run(session, profile, FakeBehaviour.near_miss)

    assert record.status is ImportStatus.failed
    assert proposals.list_for(session, profile) == []


def test_a_field_with_no_quote_never_reaches_the_review_queue(session, profile):
    record = _run(session, profile, FakeBehaviour.quote_missing)

    assert record.status is ImportStatus.failed
    assert proposals.list_for(session, profile) == []


def test_every_value_in_every_proposal_appears_in_the_source(session, profile):
    """The invariant, stated directly: SC-003, zero fabricated fields."""
    from app.imports.evidence import quote_is_supported

    _run(session, profile, FakeBehaviour.extract)

    for proposal in proposals.list_for(session, profile):
        assert proposal.evidence, "a proposal without evidence cannot be trusted"
        for name, record in proposal.evidence.items():
            assert quote_is_supported(record["quote"], SOURCE), (
                f"{name} carries a quote that is not in the source"
            )
            assert record["verified"] is True


def test_a_whitespace_variant_is_accepted(session, profile):
    """Extracted text differs from the original in spacing; that must not fail."""
    record = _run(session, profile, FakeBehaviour.whitespace_variant)

    assert record.status is ImportStatus.completed
    assert len(proposals.list_for(session, profile)) == 1


def test_extraction_writes_nothing_to_the_profile(session, profile):
    """Gate G6: only the user moves anything into their profile."""
    _run(session, profile, FakeBehaviour.extract)

    assert career_service.list_entries(session, profile, "experiences") == []
    assert career_service.list_entries(session, profile, "skills") == []
