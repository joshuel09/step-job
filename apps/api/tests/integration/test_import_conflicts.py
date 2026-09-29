"""Quickstart Scenario 5 — a self-contradictory document is flagged, not fixed.

Real resumes contain mistakes. Picking the likelier reading would mean deciding
what someone's career was rather than reporting what their document says, which
is the fabrication Principle IV forbids wearing a helpful face (FR-012b).
"""

import pytest
from app.career import proposals
from app.career import service as career_service
from app.imports.conflicts import detect, detect_across


class TestDetect:
    def test_an_end_before_a_start_is_flagged(self):
        conflicts = detect({"started_on": "2024-03-01", "ended_on": "2021-01-01"})

        assert len(conflicts) == 1
        assert set(conflicts[0]["fields"]) == {"started_on", "ended_on"}

    def test_a_valid_range_is_not_flagged(self):
        assert detect({"started_on": "2021-01-01", "ended_on": "2024-03-01"}) == []

    def test_an_ongoing_role_is_not_flagged(self):
        assert detect({"started_on": "2021-01-01", "ended_on": None}) == []

    def test_an_expiry_before_an_issue_date_is_flagged(self):
        conflicts = detect({"issued_on": "2024-01-01", "expires_on": "2020-01-01"})
        assert set(conflicts[0]["fields"]) == {"issued_on", "expires_on"}

    def test_the_dates_are_reported_as_written(self):
        """Not swapped into a sensible order. The user decides which is wrong."""
        values = {"started_on": "2024-03-01", "ended_on": "2021-01-01"}
        detect(values)

        assert values["started_on"] == "2024-03-01"
        assert values["ended_on"] == "2021-01-01"


class TestDetectAcross:
    def test_one_role_described_twice_with_different_dates_is_flagged(self):
        found = detect_across(
            [
                {
                    "employer_name": "Example Corp",
                    "job_title": "Engineer",
                    "started_on": "2021-01-01",
                },
                {
                    "employer_name": "Example Corp",
                    "job_title": "Engineer",
                    "started_on": "2022-01-01",
                },
            ]
        )
        assert len(found) == 2, "both entries carry the disagreement"

    def test_a_promotion_is_not_flagged(self):
        """Different titles at one employer is a career, not a contradiction."""
        found = detect_across(
            [
                {
                    "employer_name": "Example Corp",
                    "job_title": "Engineer",
                    "started_on": "2019-01-01",
                },
                {
                    "employer_name": "Example Corp",
                    "job_title": "Senior Engineer",
                    "started_on": "2022-01-01",
                },
            ]
        )
        assert found == {}

    def test_different_employers_are_not_flagged(self):
        found = detect_across(
            [
                {
                    "employer_name": "Example Corp",
                    "job_title": "Engineer",
                    "started_on": "2021-01-01",
                },
                {
                    "employer_name": "Other Corp",
                    "job_title": "Engineer",
                    "started_on": "2022-01-01",
                },
            ]
        )
        assert found == {}


@pytest.fixture
def profile(session, user_id):
    return career_service.get_or_create_profile(session, user_id)


def test_a_conflicted_proposal_still_reaches_review(session, profile):
    """Flagged, not withheld. The user corrects it and accepts (FR-012c)."""
    from app.career import models

    session.add(
        models.ProposedEntry(
            profile_id=profile.id,
            entry_type=models.ProposedEntryType.work_experience,
            source="import:pasted_text",
            payload={
                "employer_name": "Example Corp",
                "job_title": "Engineer",
                "started_on": "2024-03-01",
                "ended_on": "2021-01-01",
            },
            conflicts=[{"fields": ["started_on", "ended_on"], "reason": "end before start"}],
        )
    )
    session.flush()

    queued = proposals.list_for(session, profile)
    assert len(queued) == 1
    assert queued[0].conflicts


def test_correcting_a_conflict_lets_the_entry_be_accepted(client, auth_headers, session):
    from app.career import models

    assert client.post("/api/v1/profile", headers=auth_headers).status_code == 201
    profile = career_service.require_profile(
        session, __import__("uuid").UUID(auth_headers["Authorization"].split()[1])
    )

    session.add(
        models.ProposedEntry(
            profile_id=profile.id,
            entry_type=models.ProposedEntryType.work_experience,
            source="import:pasted_text",
            payload={
                "employer_name": "Example Corp",
                "job_title": "Engineer",
                "started_on": "2024-03-01",
                "ended_on": "2021-01-01",
            },
            conflicts=[{"fields": ["started_on", "ended_on"], "reason": "end before start"}],
        )
    )
    session.flush()

    proposal = client.get("/api/v1/profile/proposals", headers=auth_headers).json()[0]

    # As written, the profile refuses it — the same validation that protects a
    # hand-entered role.
    assert (
        client.post(
            f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers
        ).status_code
        == 422
    )

    corrected = client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/accept",
        headers=auth_headers,
        json={"payload": {"ended_on": "2024-06-01"}},
    )
    assert corrected.status_code == 201
