"""Quickstart Scenario 1 — record a career and read it back.

Covers User Story 1's independent test and SC-007: every value a user enters is
still present and unchanged when they come back.
"""

import uuid


def _profile(client, headers) -> None:
    assert client.post("/api/v1/profile", headers=headers).status_code == 201


def test_experience_round_trips_unchanged(client, auth_headers):
    _profile(client, auth_headers)

    created = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={
            "employer_name": "Example Corp",
            "job_title": "Software Engineer",
            "employment_type": "permanent",
            "started_on": "2021-04-01",
            "ended_on": None,
            "description": "Built and maintained internal services.",
            "source_language": "en",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["job_title"] == "Software Engineer"
    assert body["ended_on"] is None, "a null end date means ongoing and must be preserved"

    profile = client.get("/api/v1/profile", headers=auth_headers).json()
    stored = profile["experiences"][0]
    assert stored["employer_name"] == "Example Corp"
    assert stored["description"] == "Built and maintained internal services."


def test_end_date_before_start_is_rejected_with_a_reason(client, auth_headers):
    _profile(client, auth_headers)

    response = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={
            "employer_name": "Example Corp",
            "job_title": "Engineer",
            "started_on": "2024-01-01",
            "ended_on": "2023-01-01",
            "source_language": "en",
        },
    )
    assert response.status_code == 422
    failures = response.json()["failures"]
    # FR-014: the interface must be able to show which field was wrong and why.
    assert failures[0]["field"] == "ended_on"
    assert "on or after" in failures[0]["reason"]


def test_overlapping_experiences_are_accepted_without_warning(client, auth_headers):
    _profile(client, auth_headers)
    common = {"job_title": "Engineer", "source_language": "en"}

    first = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={**common, "employer_name": "Example Corp", "started_on": "2021-01-01"},
    )
    second = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={**common, "employer_name": "Other Corp", "started_on": "2022-01-01"},
    )
    # Concurrent roles and contract work are normal, not an error.
    assert first.status_code == 201
    assert second.status_code == 201


def test_deleting_an_experience_warns_about_linked_stories(client, auth_headers, session):
    from app.career import models, service

    _profile(client, auth_headers)
    created = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={
            "employer_name": "Example Corp",
            "job_title": "Engineer",
            "started_on": "2021-01-01",
            "source_language": "en",
        },
    ).json()

    profile = service.require_profile(session, uuid.UUID(auth_headers["Authorization"].split()[1]))
    session.add(
        models.CareerStory(
            profile_id=profile.id,
            work_experience_id=uuid.UUID(created["id"]),
            title="Cut processing errors",
            challenge="Manual steps caused mistakes.",
            action="Reworked the update flow.",
            result="Errors fell substantially.",
        )
    )
    session.flush()

    # FR-013: the first attempt reports what depends on the entry and changes nothing.
    blocked = client.delete(f"/api/v1/profile/experiences/{created['id']}", headers=auth_headers)
    assert blocked.status_code == 409
    assert client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]

    confirmed = client.delete(
        f"/api/v1/profile/experiences/{created['id']}?confirm=true", headers=auth_headers
    )
    assert confirmed.status_code == 204


def test_completeness_reports_empty_sections(client, auth_headers):
    _profile(client, auth_headers)
    report = client.get("/api/v1/profile/completeness", headers=auth_headers).json()

    # FR-015: an incomplete profile is valid and the gaps are visible.
    assert report["experiences"] == {"complete": False, "entry_count": 0}
    assert report["identity"]["complete"] is False
