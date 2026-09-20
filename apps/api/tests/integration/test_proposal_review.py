"""Quickstart Scenario 3 — nothing enters the profile unreviewed.

The invisibility check is the one that matters: if a pending proposal shows up
in a profile read, an outside source has effectively written to the user's
career record without asking. That is a gate G6 failure, not a display bug.
"""

import uuid

EXPERIENCE = {
    "employer_name": "Example Corp",
    "job_title": "Software Engineer",
    "started_on": "2021-04-01",
    "source_language": "en",
}


def _profile_with_experience(client, headers) -> str:
    assert client.post("/api/v1/profile", headers=headers).status_code == 201
    return client.post("/api/v1/profile/experiences", headers=headers, json=EXPERIENCE).json()["id"]


def _propose(client, headers, payload, entry_type="work_experience"):
    response = client.post(
        "/api/v1/profile/proposals",
        headers=headers,
        json=[{"entry_type": entry_type, "source": "manual-test-fixture", "payload": payload}],
    )
    assert response.status_code == 201, response.text
    return response.json()[0]


def test_a_pending_proposal_is_invisible_to_the_profile(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    _propose(client, auth_headers, {**EXPERIENCE, "job_title": "Backend Engineer"})

    profile = client.get("/api/v1/profile", headers=auth_headers).json()
    titles = [e["job_title"] for e in profile["experiences"]]

    assert "Backend Engineer" not in titles
    assert len(profile["experiences"]) == 1


def test_a_proposal_records_where_it_came_from(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    proposal = _propose(client, auth_headers, EXPERIENCE)

    assert proposal["source"] == "manual-test-fixture"
    assert proposal["status"] == "pending"


def test_a_differently_worded_title_at_the_same_employer_is_flagged(client, auth_headers):
    """Two sources describing one role is the realistic duplicate case."""
    experience_id = _profile_with_experience(client, auth_headers)

    proposal = _propose(
        client,
        auth_headers,
        {**EXPERIENCE, "employer_name": "Example Corp.", "job_title": "Backend Engineer"},
    )
    assert proposal["possible_duplicate_of"] == experience_id


def test_a_promotion_is_not_flagged_as_a_duplicate(client, auth_headers):
    """Same employer, no overlap — a later role, not the same one (FR-033)."""
    experience_id = _profile_with_experience(client, auth_headers)
    client.patch(
        f"/api/v1/profile/experiences/{experience_id}",
        headers=auth_headers,
        json={"ended_on": "2022-03-31"},
    )

    proposal = _propose(
        client,
        auth_headers,
        {**EXPERIENCE, "job_title": "Senior Engineer", "started_on": "2023-01-01"},
    )
    assert proposal["possible_duplicate_of"] is None


def test_accepting_writes_the_corrected_version(client, auth_headers):
    """FR-019: what the user approved is what the profile holds."""
    _profile_with_experience(client, auth_headers)
    proposal = _propose(
        client, auth_headers, {**EXPERIENCE, "employer_name": "Other Corp", "job_title": "Engineer"}
    )

    accepted = client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/accept",
        headers=auth_headers,
        json={"payload": {"job_title": "Senior Backend Engineer"}},
    )
    assert accepted.status_code == 201, accepted.text

    profile = client.get("/api/v1/profile", headers=auth_headers).json()
    titles = [e["job_title"] for e in profile["experiences"]]
    assert "Senior Backend Engineer" in titles
    assert "Engineer" not in titles, "the uncorrected proposal must not reach the profile"


def test_accepting_twice_is_a_conflict(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    proposal = _propose(client, auth_headers, {**EXPERIENCE, "employer_name": "Other Corp"})

    assert (
        client.post(
            f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers
        ).status_code
        == 409
    )


def test_rejecting_creates_nothing(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    proposal = _propose(client, auth_headers, {**EXPERIENCE, "employer_name": "Other Corp"})

    assert (
        client.post(
            f"/api/v1/profile/proposals/{proposal['id']}/reject", headers=auth_headers
        ).status_code
        == 204
    )
    assert len(client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]) == 1
    assert client.get("/api/v1/profile/proposals", headers=auth_headers).json() == []


def test_a_rejected_proposal_cannot_be_accepted_afterwards(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    proposal = _propose(client, auth_headers, {**EXPERIENCE, "employer_name": "Other Corp"})

    client.post(f"/api/v1/profile/proposals/{proposal['id']}/reject", headers=auth_headers)
    assert (
        client.post(
            f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers
        ).status_code
        == 409
    )


def test_merging_updates_the_existing_entry_rather_than_adding_one(client, auth_headers):
    experience_id = _profile_with_experience(client, auth_headers)
    proposal = _propose(
        client, auth_headers, {**EXPERIENCE, "job_title": "Backend Engineer"}
    )

    merged = client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/merge",
        headers=auth_headers,
        json={"target_entry_id": experience_id, "payload": {"job_title": "Backend Engineer"}},
    )
    assert merged.status_code == 200, merged.text

    experiences = client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]
    assert len(experiences) == 1, "merging must not leave two entries"
    assert experiences[0]["job_title"] == "Backend Engineer"


def test_keeping_both_remains_available(client, auth_headers):
    """FR-034: a flagged duplicate is a suggestion, never an automatic merge."""
    _profile_with_experience(client, auth_headers)
    proposal = _propose(client, auth_headers, {**EXPERIENCE, "job_title": "Backend Engineer"})
    assert proposal["possible_duplicate_of"] is not None

    client.post(f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers)

    experiences = client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]
    assert len(experiences) == 2, "accepting a flagged proposal must keep both"


def test_a_proposal_from_another_profile_is_not_found(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    response = client.post(
        f"/api/v1/profile/proposals/{uuid.uuid4()}/accept", headers=auth_headers
    )
    assert response.status_code == 404
