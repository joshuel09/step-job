"""Quickstart Scenario 2 — keep an accomplishment and find it later.

SC-006 expects a user to retrieve something they recorded three months earlier in
under a minute. Nobody remembers the title they gave it, so search across every
field is the requirement, not a nicety.
"""

import uuid


def _profile_with_experience(client, headers) -> str:
    assert client.post("/api/v1/profile", headers=headers).status_code == 201
    return client.post(
        "/api/v1/profile/experiences",
        headers=headers,
        json={
            "employer_name": "Example Corp",
            "job_title": "Software Engineer",
            "started_on": "2021-04-01",
            "source_language": "en",
        },
    ).json()["id"]


STORY = {
    "title": "Cut order processing errors",
    "challenge": "Manual steps caused frequent mistakes.",
    "action": "Reworked the update flow and added validation.",
    "result": "Operational errors fell substantially.",
    "source_language": "en",
}


def test_a_story_is_stored_and_linked_to_its_role(client, auth_headers):
    experience_id = _profile_with_experience(client, auth_headers)

    created = client.post(
        "/api/v1/profile/stories",
        headers=auth_headers,
        json={**STORY, "work_experience_id": experience_id},
    )
    assert created.status_code == 201, created.text
    assert created.json()["work_experience_id"] == experience_id


def test_a_story_appears_alongside_its_experience(client, auth_headers):
    experience_id = _profile_with_experience(client, auth_headers)
    client.post(
        "/api/v1/profile/stories",
        headers=auth_headers,
        json={**STORY, "work_experience_id": experience_id},
    )

    detail = client.get(f"/api/v1/profile/experiences/{experience_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert [s["title"] for s in detail.json()["stories"]] == ["Cut order processing errors"]


def test_a_story_without_a_role_is_valid(client, auth_headers):
    """Not every accomplishment belongs to a job the user has recorded."""
    _profile_with_experience(client, auth_headers)

    created = client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY)
    assert created.status_code == 201
    assert created.json()["work_experience_id"] is None


def test_search_matches_the_result_not_only_the_title(client, auth_headers):
    """The detail a user remembers is rarely the title they chose."""
    _profile_with_experience(client, auth_headers)
    client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY)

    found = client.get("/api/v1/profile/stories?q=operational", headers=auth_headers).json()
    assert len(found) == 1

    by_action = client.get("/api/v1/profile/stories?q=validation", headers=auth_headers).json()
    assert len(by_action) == 1


def test_search_is_case_insensitive(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY)

    assert len(client.get("/api/v1/profile/stories?q=ORDER", headers=auth_headers).json()) == 1


def test_search_returns_nothing_for_an_unmatched_term(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY)

    assert client.get("/api/v1/profile/stories?q=unrelated", headers=auth_headers).json() == []


def test_an_empty_query_returns_everything(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY)

    assert len(client.get("/api/v1/profile/stories", headers=auth_headers).json()) == 1


def test_a_story_cannot_be_linked_to_someone_elses_role(client, auth_headers):
    """That would file an accomplishment under a role its author never held."""
    _profile_with_experience(client, auth_headers)

    response = client.post(
        "/api/v1/profile/stories",
        headers=auth_headers,
        json={**STORY, "work_experience_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422
    assert response.json()["failures"][0]["field"] == "work_experience_id"


def test_a_story_can_be_edited_and_deleted(client, auth_headers):
    _profile_with_experience(client, auth_headers)
    story_id = client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY).json()["id"]

    edited = client.patch(
        f"/api/v1/profile/stories/{story_id}",
        headers=auth_headers,
        json={"result": "Errors fell by a third."},
    )
    assert edited.status_code == 200
    assert edited.json()["result"] == "Errors fell by a third."
    assert edited.json()["challenge"] == STORY["challenge"], "an edit must not blank other fields"

    assert (
        client.delete(f"/api/v1/profile/stories/{story_id}", headers=auth_headers).status_code
        == 204
    )
    assert client.get("/api/v1/profile/stories", headers=auth_headers).json() == []


def test_deleting_a_role_still_warns_about_its_stories(client, auth_headers):
    """FR-013 held for stories before this story was built; it must still hold."""
    experience_id = _profile_with_experience(client, auth_headers)
    client.post(
        "/api/v1/profile/stories",
        headers=auth_headers,
        json={**STORY, "work_experience_id": experience_id},
    )

    blocked = client.delete(f"/api/v1/profile/experiences/{experience_id}", headers=auth_headers)
    assert blocked.status_code == 409
