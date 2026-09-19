"""Quickstart Scenario 4 — a snapshot survives an edit of its source entry.

This is the check most likely to be quietly broken by a later change, and the
one Principle IV rests on: if a snapshot moves with the entry it captured, then
a generated document's claims can no longer be traced to anything real.
"""

import uuid


def _profile_with_experience(client, headers) -> str:
    assert client.post("/api/v1/profile", headers=headers).status_code == 201
    created = client.post(
        "/api/v1/profile/experiences",
        headers=headers,
        json={
            "employer_name": "Example Corp",
            "job_title": "Software Engineer",
            "started_on": "2021-04-01",
            "description": "Built internal services.",
            "source_language": "en",
        },
    )
    assert created.status_code == 201
    return created.json()["id"]


def test_snapshot_keeps_the_wording_it_captured(client, auth_headers):
    experience_id = _profile_with_experience(client, auth_headers)

    captured = client.post(
        "/api/v1/profile/snapshots",
        headers=auth_headers,
        json={"document_ref": "resume-2026-09", "entry_ids": [experience_id]},
    )
    assert captured.status_code == 201, captured.text
    snapshot_id = captured.json()["id"]

    # The user rewrites the role after the document was generated.
    changed = client.patch(
        f"/api/v1/profile/experiences/{experience_id}",
        headers=auth_headers,
        json={"job_title": "Completely Different Title"},
    )
    assert changed.status_code == 200
    assert changed.json()["job_title"] == "Completely Different Title"

    snapshot = client.get(f"/api/v1/profile/snapshots/{snapshot_id}", headers=auth_headers).json()
    captured_entry = snapshot["payload"][experience_id]

    # The document's claims still trace to what they were actually based on.
    assert captured_entry["job_title"] == "Software Engineer"


def test_snapshot_outlives_the_entry_it_captured(client, auth_headers):
    experience_id = _profile_with_experience(client, auth_headers)

    snapshot_id = client.post(
        "/api/v1/profile/snapshots",
        headers=auth_headers,
        json={"document_ref": "resume-2026-09", "entry_ids": [experience_id]},
    ).json()["id"]

    assert (
        client.delete(
            f"/api/v1/profile/experiences/{experience_id}?confirm=true", headers=auth_headers
        ).status_code
        == 204
    )

    snapshot = client.get(f"/api/v1/profile/snapshots/{snapshot_id}", headers=auth_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["payload"][experience_id]["job_title"] == "Software Engineer"


def test_snapshot_records_which_entries_it_captured(client, auth_headers):
    """FR-010: traceability runs both ways — to the content, and back to the entry."""
    experience_id = _profile_with_experience(client, auth_headers)

    snapshot = client.post(
        "/api/v1/profile/snapshots",
        headers=auth_headers,
        json={"document_ref": "resume-2026-09", "entry_ids": [experience_id]},
    ).json()

    assert snapshot["captured_entry_ids"] == [experience_id]


def test_capturing_an_entry_that_is_not_yours_is_rejected(client, auth_headers):
    """A traceability record that could capture another profile would itself leak."""
    _profile_with_experience(client, auth_headers)

    response = client.post(
        "/api/v1/profile/snapshots",
        headers=auth_headers,
        json={"document_ref": "resume", "entry_ids": [str(uuid.uuid4())]},
    )
    assert response.status_code == 422
    assert response.json()["failures"][0]["field"] == "entry_ids"


def test_capturing_nothing_is_rejected(client, auth_headers):
    _profile_with_experience(client, auth_headers)

    response = client.post(
        "/api/v1/profile/snapshots",
        headers=auth_headers,
        json={"document_ref": "resume", "entry_ids": []},
    )
    assert response.status_code == 422
