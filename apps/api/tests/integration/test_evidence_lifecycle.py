"""Quickstart Scenario 7 — evidence is discarded when a proposal is reviewed.

Evidence exists so a user can judge a value before accepting it. Afterwards it is
a fragment of someone's resume, which may state residence status, an address or a
previous salary, with no remaining purpose (FR-015a).

The second half matters as much: discarding it must not disturb what the user
approved (FR-015b).
"""

SOURCE = "Software Engineer, Example Corp\nApril 2021 to March 2024\nBuilt internal services."


def _profile_with_proposals(client, headers):
    assert client.post("/api/v1/profile", headers=headers).status_code == 201
    client.post("/api/v1/profile/imports", headers=headers, json={"text": SOURCE})
    queued = client.get("/api/v1/profile/proposals", headers=headers).json()
    assert queued, "expected the import to produce something to review"
    return queued[0]


def test_evidence_is_present_while_the_decision_is_pending(client, auth_headers):
    proposal = _profile_with_proposals(client, auth_headers)
    assert proposal["evidence"] is not None


def test_evidence_is_gone_once_the_proposal_is_accepted(client, auth_headers):
    proposal = _profile_with_proposals(client, auth_headers)

    accepted = client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers
    )
    assert accepted.status_code == 201

    reviewed = client.get(
        "/api/v1/profile/proposals?status=accepted", headers=auth_headers
    ).json()
    assert reviewed[0]["evidence"] is None


def test_evidence_is_gone_once_the_proposal_is_rejected(client, auth_headers):
    proposal = _profile_with_proposals(client, auth_headers)

    assert (
        client.post(
            f"/api/v1/profile/proposals/{proposal['id']}/reject", headers=auth_headers
        ).status_code
        == 204
    )

    reviewed = client.get(
        "/api/v1/profile/proposals?status=rejected", headers=auth_headers
    ).json()
    assert reviewed[0]["evidence"] is None


def test_discarding_evidence_leaves_the_accepted_entry_alone(client, auth_headers):
    """FR-015b: what the user approved stays exactly as approved."""
    proposal = _profile_with_proposals(client, auth_headers)
    proposed_title = proposal["payload"]["job_title"]

    client.post(f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers)

    experiences = client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]
    assert len(experiences) == 1
    assert experiences[0]["job_title"] == proposed_title


def test_a_correction_survives_the_evidence_being_discarded(client, auth_headers):
    proposal = _profile_with_proposals(client, auth_headers)

    client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/accept",
        headers=auth_headers,
        json={"payload": {"job_title": "Senior Backend Engineer"}},
    )

    experiences = client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]
    assert experiences[0]["job_title"] == "Senior Backend Engineer"


def test_an_incomplete_proposal_names_the_field_it_needs(client, auth_headers, session):
    """An import may legitimately find no start date.

    FR-008 leaves an unsupported field empty rather than inventing one, so a
    proposal can arrive without something the profile requires. Completing it in
    review is the intended path — what must not happen is the request failing
    with a database error that names no field.
    """
    from app.career import models
    from app.career import service as career_service

    assert client.post("/api/v1/profile", headers=auth_headers).status_code == 201
    profile = career_service.require_profile(
        session, __import__("uuid").UUID(auth_headers["Authorization"].split()[1])
    )

    session.add(
        models.ProposedEntry(
            profile_id=profile.id,
            entry_type=models.ProposedEntryType.work_experience,
            source="import:pasted_text",
            payload={"employer_name": "Example Corp", "job_title": "Engineer"},
            evidence={"job_title": {"quote": "Engineer", "verified": True}},
        )
    )
    session.flush()

    proposal = client.get("/api/v1/profile/proposals", headers=auth_headers).json()[0]
    response = client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/accept", headers=auth_headers
    )

    assert response.status_code == 422
    assert [f["field"] for f in response.json()["failures"]] == ["started_on"]


def test_supplying_the_missing_field_lets_it_be_accepted(client, auth_headers, session):
    from app.career import models
    from app.career import service as career_service

    assert client.post("/api/v1/profile", headers=auth_headers).status_code == 201
    profile = career_service.require_profile(
        session, __import__("uuid").UUID(auth_headers["Authorization"].split()[1])
    )

    session.add(
        models.ProposedEntry(
            profile_id=profile.id,
            entry_type=models.ProposedEntryType.work_experience,
            source="import:pasted_text",
            payload={"employer_name": "Example Corp", "job_title": "Engineer"},
        )
    )
    session.flush()

    proposal = client.get("/api/v1/profile/proposals", headers=auth_headers).json()[0]
    accepted = client.post(
        f"/api/v1/profile/proposals/{proposal['id']}/accept",
        headers=auth_headers,
        json={"payload": {"started_on": "2021-04-01"}},
    )

    assert accepted.status_code == 201
