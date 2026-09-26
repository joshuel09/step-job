"""Quickstart Scenario 1 — paste a career and get reviewable proposals.

User Story 1's independent test: proposals appear with their evidence, and the
profile is untouched until the user accepts something.
"""

SOURCE = "Software Engineer, Example Corp\nApril 2021 to March 2024\nBuilt internal services."


def _profile(client, headers):
    assert client.post("/api/v1/profile", headers=headers).status_code == 201


def test_pasting_text_creates_reviewable_proposals(client, auth_headers):
    _profile(client, auth_headers)

    created = client.post("/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE})
    assert created.status_code == 201, created.text

    body = created.json()
    assert body["source_kind"] == "pasted_text"
    assert body["status"] == "completed"
    assert body["entry_count"] >= 1


def test_each_proposal_shows_the_words_it_came_from(client, auth_headers):
    _profile(client, auth_headers)
    client.post("/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE})

    queued = client.get("/api/v1/profile/proposals", headers=auth_headers).json()
    assert queued

    evidence = queued[0]["evidence"]
    assert evidence, "a user cannot judge a value without seeing where it came from"
    for record in evidence.values():
        assert record["quote"]
        assert record["verified"] is True


def test_the_profile_is_untouched_until_the_user_accepts(client, auth_headers):
    """Gate G6, checked through the API rather than the service."""
    _profile(client, auth_headers)
    client.post("/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE})

    profile = client.get("/api/v1/profile", headers=auth_headers).json()
    assert profile["experiences"] == []


def test_a_proposal_records_the_import_it_came_from(client, auth_headers):
    _profile(client, auth_headers)
    created = client.post(
        "/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE}
    ).json()

    queued = client.get("/api/v1/profile/proposals", headers=auth_headers).json()
    assert queued[0]["import_id"] == created["id"]


def test_an_import_can_be_followed_to_its_outcome(client, auth_headers):
    _profile(client, auth_headers)
    created = client.post(
        "/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE}
    ).json()

    detail = client.get(f"/api/v1/profile/imports/{created['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["outcome"]["message"]


def test_imports_are_listed_most_recent_first(client, auth_headers):
    _profile(client, auth_headers)
    client.post("/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE})
    client.post("/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE})

    listed = client.get("/api/v1/profile/imports", headers=auth_headers).json()
    assert len(listed) == 2


def test_an_import_record_carries_no_filename(client, auth_headers):
    """FR-019b: a name can reveal where someone was applying."""
    _profile(client, auth_headers)
    created = client.post(
        "/api/v1/profile/imports", headers=auth_headers, json={"text": SOURCE}
    ).json()

    assert "filename" not in created
    assert "file_name" not in created


def test_empty_text_is_rejected(client, auth_headers):
    _profile(client, auth_headers)
    response = client.post("/api/v1/profile/imports", headers=auth_headers, json={"text": ""})
    assert response.status_code == 422


def test_another_profiles_import_is_not_found(client, auth_headers):
    import uuid

    _profile(client, auth_headers)
    response = client.get(f"/api/v1/profile/imports/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
